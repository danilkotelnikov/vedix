#!/usr/bin/env python3
"""Open-access corpus scraper — pulls top-cited OA papers directly from
the publisher (or repository) via OpenAlex's ``best_oa_location.pdf_url``.

This script complements ``scrape_journals.py``: that one uses Anna's
Archive to fetch paywalled content (rate-limited, daily quota); this one
sticks to genuinely OA papers and downloads directly from the
publisher's CDN. No quota, no rate limit beyond polite-pool OpenAlex
throttling.

Coverage strategy
-----------------

Two modes, picked via CLI:

1. ``--mix``: curated 9-paper queue across OA-flagship journals
   (Nature Communications, PLoS Biology, eLife, Chemical Science,
   ACS Central Science, Physical Review X, BMC Biology, …). Restricts
   per-target to ``primary_location.source.issn:<ISSN>`` so we know
   exactly which venue we're sampling.

2. ``--discipline X``: open mode — query top OA papers for that
   discipline's OpenAlex concept, no ISSN restriction. Useful when you
   just want "more chemistry register data" regardless of venue.

Output goes to ``~/.vedix/corpus/<discipline>/en/{pdf,text}/`` so it
merges with the bridged Nature corpus and the Anna's-acquired papers.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

import httpx


USER_AGENT = "vedix/3.0 (research workbench; mailto:OPENALEX_EMAIL)"

# Some publishers' CDNs reject the polite-pool UA with 403. For the
# download step we use a browser-like header set; for OpenAlex API calls
# we keep the polite UA so we stay in the polite pool.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


def _elife_pdf_url_from_doi(doi: str) -> str | None:
    """Construct the eLife CDN PDF URL from a 10.7554/elife.<id> DOI."""
    m = re.match(r"10\.7554/elife\.(\d+)", doi, re.IGNORECASE)
    if not m:
        return None
    paper_id = m.group(1)
    return f"https://cdn.elifesciences.org/articles/{paper_id}/elife-{paper_id}-v1.pdf"


def _frontiers_pdf_url_from_doi(doi: str) -> str | None:
    """Construct the Frontiers PDF URL from a 10.3389/<journal>.<year>.<id> DOI.

    Frontiers serves PDFs at a stable URL through the journal browser
    page. The Azure-blob URLs OpenAlex sometimes records are signed and
    expire after a few months — bypass them with the canonical route.
    """
    if not doi.lower().startswith("10.3389/"):
        return None
    return f"https://www.frontiersin.org/articles/{doi}/pdf"


def _arxiv_pdf_url_from_doi(doi: str) -> str | None:
    """Try to derive an arXiv preprint URL from a journal DOI.

    Physical Review X papers usually have an arXiv preprint with a
    matching arXiv ID embedded in OpenAlex's ``locations`` array, but
    OpenAlex's ``best_oa_location.pdf_url`` sometimes routes to the
    paywalled APS CDN instead. We can't infer the arXiv ID from a PRX
    DOI alone — that's resolved at query time below.

    Kept as a stub so the recovery path stays readable.
    """
    _ = doi
    return None

# OpenAlex level-0 / level-1 concept IDs for the seven disciplines we
# train register classifiers against.
DISCIPLINE_CONCEPTS: dict[str, str] = {
    "chemistry":        "C185592680",
    "physics":          "C121332964",
    "biology":          "C86803240",
    "medicine":         "C71924100",
    "computer_science": "C41008148",
    "materials":        "C192562407",
    "geology":          "C127313418",
}


# OA-flagship journals, indexed by ISSN. The ``oa_status`` column
# indicates the OpenAlex classification when querying papers from
# this venue: ``gold`` (fully OA at the venue) or ``hybrid`` (the
# venue is paywalled but the specific paper is OA via author opt-in).
OA_JOURNALS: dict[str, dict[str, str]] = {
    "nature-communications":   {"issn": "2041-1723", "full_name": "Nature Communications", "oa_status": "gold"},
    "scientific-reports":      {"issn": "2045-2322", "full_name": "Scientific Reports",    "oa_status": "gold"},
    "plos-biology":            {"issn": "1544-9173", "full_name": "PLoS Biology",          "oa_status": "gold"},
    "plos-medicine":           {"issn": "1549-1277", "full_name": "PLoS Medicine",         "oa_status": "gold"},
    "plos-one":                {"issn": "1932-6203", "full_name": "PLoS ONE",              "oa_status": "gold"},
    "elife":                   {"issn": "2050-084X", "full_name": "eLife",                  "oa_status": "gold"},
    "bmc-biology":             {"issn": "1741-7007", "full_name": "BMC Biology",            "oa_status": "gold"},
    "chemical-science":        {"issn": "2041-6520", "full_name": "Chemical Science",       "oa_status": "gold"},
    "acs-central-science":     {"issn": "2374-7943", "full_name": "ACS Central Science",    "oa_status": "gold"},
    "physical-review-x":       {"issn": "2160-3308", "full_name": "Physical Review X",      "oa_status": "gold"},
    "frontiers-microbiology":  {"issn": "1664-302X", "full_name": "Frontiers in Microbiology", "oa_status": "gold"},
    "frontiers-chemistry":     {"issn": "2296-2646", "full_name": "Frontiers in Chemistry",    "oa_status": "gold"},
    "nature-comms-earth-env":  {"issn": "2662-4435", "full_name": "Communications Earth & Environment", "oa_status": "gold"},
}


# Curated 9-paper queue. Mix balances:
# - 3 chemistry venues (RSC, ACS, NComms — three different OA editorial styles)
# - 3 biology venues (PLoS Bio, eLife, BMC Bio)
# - 1 physics (PRX — highest-rigor OA physics venue)
# - 1 medicine (PLoS Medicine)
# - 1 computer-science (Nature Comms CS-tagged papers — full coverage rare in OA)
DEFAULT_MIX: list[tuple[str, str, int]] = [
    ("chemical-science",       "chemistry", 1),
    ("acs-central-science",    "chemistry", 1),
    ("nature-communications",  "chemistry", 1),
    ("plos-biology",           "biology",   1),
    ("elife",                  "biology",   1),
    ("bmc-biology",            "biology",   1),
    ("physical-review-x",      "physics",   1),
    ("plos-medicine",          "medicine",  1),
    ("nature-communications",  "computer_science", 1),
]


async def query_openalex_oa(
    *, target: int, candidates: int, email: str,
    issn: str | None, concept_id: str | None,
    from_year: int, to_year: int | None,
    log: logging.Logger,
) -> list[dict]:
    """Query OpenAlex for top-cited OA papers matching the filters.

    Filters:
      - ``is_oa:true`` (genuine OA — not green-OA "repository preprint")
      - ``type:article`` (not journals, datasets, book chapters)
      - ``language:en``
      - optional ISSN + concept restriction

    The returned list keeps only works with a non-null
    ``best_oa_location.pdf_url`` and a normalised DOI.
    """
    filter_parts = [
        "is_oa:true",
        "type:article",
        "language:en",
        f"from_publication_date:{from_year}-01-01",
    ]
    if to_year is not None:
        filter_parts.append(f"to_publication_date:{to_year}-12-31")
    if issn is not None:
        filter_parts.append(f"primary_location.source.issn:{issn}")
    if concept_id is not None:
        filter_parts.append(f"concepts.id:{concept_id}")

    params = {
        "filter": ",".join(filter_parts),
        "per_page": min(candidates, 200),
        "sort": "cited_by_count:desc",
        "mailto": email,
    }
    log.info(
        "OpenAlex OA query: ISSN=%s concept=%s from=%s candidates=%d (target %d)",
        issn, concept_id, from_year, candidates, target,
    )
    async with httpx.AsyncClient(
        timeout=60, follow_redirects=True,
        headers={"User-Agent": USER_AGENT.replace("OPENALEX_EMAIL", email)},
    ) as c:
        r = await c.get("https://api.openalex.org/works", params=params)
        r.raise_for_status()
        data = r.json()

    raw = data.get("results", [])
    log.info("OpenAlex returned %d works (meta.count=%s)",
             len(raw), data.get("meta", {}).get("count"))

    works: list[dict] = []
    for w in raw:
        doi_url = w.get("doi") or ""
        if not doi_url:
            continue
        doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        if not doi.startswith("10."):
            continue

        # Walk every OA location (not just best_oa_location) and gather
        # candidate PDF URLs. This catches papers where best_oa is
        # missing pdf_url but a secondary location has one (e.g. arXiv
        # preprint for a Physical Review X paper).
        candidate_urls: list[tuple[str, str, str]] = []  # (url, host, license)
        best_oa = w.get("best_oa_location") or {}
        if best_oa.get("pdf_url"):
            candidate_urls.append((
                best_oa["pdf_url"],
                ((best_oa.get("source") or {}).get("display_name") or ""),
                best_oa.get("license") or "",
            ))
        for loc in (w.get("oa_locations") or []):
            url = loc.get("pdf_url")
            if not url:
                continue
            if any(url == u for (u, _, _) in candidate_urls):
                continue
            candidate_urls.append((
                url,
                ((loc.get("source") or {}).get("display_name") or ""),
                loc.get("license") or "",
            ))

        # Last-resort publisher-pattern fallbacks when OpenAlex has no
        # pdf_url at all (eLife is the common case).
        if not candidate_urls:
            for fallback in (_elife_pdf_url_from_doi(doi), _arxiv_pdf_url_from_doi(doi)):
                if fallback:
                    candidate_urls.append((fallback, "publisher-pattern-fallback", ""))

        if not candidate_urls:
            continue

        works.append({
            "doi": doi,
            "title": (w.get("title") or "").strip(),
            "year": w.get("publication_year"),
            "cited_by_count": int(w.get("cited_by_count", 0)),
            "openalex_id": w.get("id"),
            "pdf_urls": [u for (u, _, _) in candidate_urls],
            "pdf_url": candidate_urls[0][0],  # primary (backcompat)
            "oa_status": (w.get("open_access") or {}).get("oa_status"),
            "license": candidate_urls[0][2],
            "version": best_oa.get("version"),
            "host": candidate_urls[0][1],
        })
    log.info("After PDF-URL filter: %d/%d works retained", len(works), len(raw))
    return works


def _safe_filename_stem(doi: str) -> str:
    """Turn a DOI into a filesystem-safe stem (no slashes, etc.)."""
    return re.sub(r"[^a-zA-Z0-9._-]", "_", doi)


async def download_pdf(
    url: str, dest: Path, *, client: httpx.AsyncClient, log: logging.Logger,
) -> bool:
    """Stream ``url`` to ``dest``; validate %PDF- magic bytes.

    Uses browser-like headers to bypass the 403 Forbidden some publisher
    CDNs (ACS, APS) return to anonymous polite-pool clients even for
    genuinely OA content.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    try:
        async with client.stream("GET", url, headers=BROWSER_HEADERS) as r:
            r.raise_for_status()
            with dest.open("wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=64_000):
                    f.write(chunk)
    except Exception as exc:  # noqa: BLE001
        log.warning("  stream failed: %s", exc)
        if dest.exists():
            dest.unlink()
        return False

    if dest.stat().st_size < 1024:
        log.warning("  file too small (%d bytes) — likely an error page", dest.stat().st_size)
        dest.unlink()
        return False
    if dest.read_bytes()[:5] != b"%PDF-":
        log.warning("  not a valid PDF (magic bytes mismatch)")
        dest.unlink()
        return False
    return True


async def download_pdf_with_fallbacks(
    urls: list[str], dest: Path, *, client: httpx.AsyncClient, log: logging.Logger,
) -> tuple[bool, str | None]:
    """Try each URL in order; return (success, the_url_that_worked)."""
    for url in urls:
        log.info("  -> %s", url)
        if await download_pdf(url, dest, client=client, log=log):
            return True, url
    return False, None


async def extract_text(pdf: Path, txt: Path, log: logging.Logger) -> bool:
    """Extract plaintext from a PDF; skip if already done."""
    if txt.exists() and txt.stat().st_size > 0:
        return True
    try:
        from pdfminer.high_level import extract_text as _pdf_text  # type: ignore[import-untyped]
    except ImportError:
        log.error("pdfminer.six not installed; run `pip install pdfminer.six`")
        return False
    try:
        text = _pdf_text(str(pdf))
    except Exception as exc:  # noqa: BLE001
        log.warning("  text extraction failed for %s: %s", pdf.name, exc)
        return False
    txt.parent.mkdir(parents=True, exist_ok=True)
    txt.write_text(text, encoding="utf-8")
    return True


async def scrape_one_target(
    *, journal: str | None, discipline: str, target_count: int,
    candidates: int, from_year: int, to_year: int,
    email: str,
    log: logging.Logger,
) -> tuple[int, int]:
    """Scrape one (journal-or-discipline, discipline) target.

    Returns ``(downloaded_count, extracted_count)``.
    """
    if journal is not None:
        preset = OA_JOURNALS[journal]
        issn = preset["issn"]
        venue_label = preset["full_name"]
    else:
        issn = None
        venue_label = "any OA venue"
    concept_id = DISCIPLINE_CONCEPTS.get(discipline)

    out_root = Path(os.path.expanduser(f"~/.vedix/corpus/{discipline}/en"))
    pdf_dir = out_root / "pdf"
    text_dir = out_root / "text"
    out_root.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("=== %s -> %s (target %d papers, OA-direct)", venue_label, discipline, target_count)
    log.info("=" * 60)

    works = await query_openalex_oa(
        target=target_count, candidates=candidates, email=email,
        issn=issn, concept_id=concept_id,
        from_year=from_year, to_year=to_year, log=log,
    )
    if not works:
        log.warning("zero OA candidates for %s/%s", venue_label, discipline)
        return 0, 0

    # Append the OpenAlex manifest (auditable provenance).
    acq_path = out_root / "acquisition.jsonl"
    with acq_path.open("a", encoding="utf-8") as f:
        for w in works:
            entry = dict(w)
            entry["source_journal"] = journal or "oa-any"
            entry["acquisition_method"] = "openalex_oa_direct"
            f.write(json.dumps(entry) + "\n")

    downloaded: list[dict] = []
    async with httpx.AsyncClient(
        timeout=120, follow_redirects=True,
        headers={"User-Agent": USER_AGENT.replace("OPENALEX_EMAIL", email)},
    ) as client:
        for i, w in enumerate(works, start=1):
            if len(downloaded) >= target_count:
                break
            title_snippet = w["title"][:80] + ("..." if len(w["title"]) > 80 else "")
            log.info("[%d/%d] cited=%d host=%s DOI=%s title=%r",
                     i, len(works), w["cited_by_count"], w["host"], w["doi"], title_snippet)

            dest_pdf = pdf_dir / f"{_safe_filename_stem(w['doi'])}.pdf"
            if dest_pdf.exists() and dest_pdf.stat().st_size > 1024 \
                    and dest_pdf.read_bytes()[:5] == b"%PDF-":
                log.info("  cache-hit pdf=%s", dest_pdf.name)
                downloaded.append(w)
                continue

            # Try every candidate URL — primary then mirrors/fallbacks
            urls_to_try: list[str] = list(w.get("pdf_urls") or [w["pdf_url"]])
            # Last-resort: append publisher-pattern fallbacks.
            for fallback in (
                _elife_pdf_url_from_doi(w["doi"]),
                _frontiers_pdf_url_from_doi(w["doi"]),
            ):
                if fallback and fallback not in urls_to_try:
                    urls_to_try.append(fallback)
            ok, used = await download_pdf_with_fallbacks(
                urls_to_try, dest_pdf, client=client, log=log,
            )
            if ok:
                log.info("  ok -> %s (%dKB) via=%s license=%s", dest_pdf.name,
                         dest_pdf.stat().st_size // 1024, used, w.get("license"))
                w["pdf_url_used"] = used
                downloaded.append(w)
            # Gentle pacing so publisher CDNs don't see a burst.
            await asyncio.sleep(0.5)

    log.info("=== %s/%s result: %d/%d papers downloaded ===",
             venue_label, discipline, len(downloaded), target_count)

    # Text extraction.
    extracted = 0
    for w in downloaded:
        pdf = pdf_dir / f"{_safe_filename_stem(w['doi'])}.pdf"
        txt = text_dir / f"{_safe_filename_stem(w['doi'])}.txt"
        if not pdf.exists():
            continue
        if await extract_text(pdf, txt, log):
            extracted += 1
    log.info("=== %s/%s extraction: %d/%d ===",
             venue_label, discipline, extracted, len(downloaded))

    # Final manifest (downloaded papers only, journal-tagged for provenance).
    dl_path = out_root / "downloaded.jsonl"
    with dl_path.open("a", encoding="utf-8") as f:
        for w in downloaded:
            entry = dict(w)
            entry["source_journal"] = journal or "oa-any"
            entry["acquisition_method"] = "openalex_oa_direct"
            f.write(json.dumps(entry) + "\n")

    return len(downloaded), extracted


async def main_async(args, log: logging.Logger) -> int:
    email = os.environ.get("OPENALEX_EMAIL", "").strip()
    if not email:
        log.error("OPENALEX_EMAIL not set in environment")
        return 1

    # Decide the queue.
    queue: list[tuple[str | None, str, int]]
    if args.mix:
        queue = [(j, d, n) for j, d, n in DEFAULT_MIX]
    elif args.queue:
        queue = []
        for spec in args.queue:
            parts = spec.split(":")
            if len(parts) != 3:
                log.error("bad --queue spec %r; expected journal:discipline:count", spec)
                return 2
            j, d, n = parts
            if j != "any" and j not in OA_JOURNALS:
                log.error("unknown OA journal %r; choose 'any' or one of %s",
                          j, sorted(OA_JOURNALS))
                return 2
            queue.append(((None if j == "any" else j), d, int(n)))
    elif args.journal and args.discipline:
        queue = [(args.journal, args.discipline, args.target_count)]
    elif args.discipline:
        # Open-mode: any OA venue, top-cited in that discipline.
        queue = [(None, args.discipline, args.target_count)]
    else:
        log.error("specify --mix, --queue, --journal+--discipline, or --discipline")
        return 2

    log.info("=" * 60)
    log.info("OA corpus scrape — %d targets queued", len(queue))
    for j, d, n in queue:
        label = OA_JOURNALS[j]["full_name"] if j else "any OA venue"
        log.info("  %-30s -> %-18s x %d", label, d, n)
    log.info("=" * 60)

    totals_dl, totals_extract = 0, 0
    for j, d, n in queue:
        try:
            dl, ex = await scrape_one_target(
                journal=j, discipline=d, target_count=n,
                candidates=args.candidates_per_target,
                from_year=args.from_year, to_year=args.to_year,
                email=email, log=log,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("target %s/%s failed: %s", j, d, exc)
            continue
        totals_dl += dl
        totals_extract += ex

    print()
    print("OA corpus build summary")
    print("-" * 60)
    print(f"  targets:    {len(queue)}")
    print(f"  downloaded: {totals_dl}")
    print(f"  extracted:  {totals_extract}")
    print()
    print("Next: python scripts/prepare_corpus.py --only-pair <discipline>:en -v")
    print()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mix", action="store_true",
                    help="Run the curated 9-paper OA-flagship mix.")
    ap.add_argument("--queue", nargs="*",
                    help="Custom queue: journal:discipline:count triples. "
                         "Use 'any' as journal for open-discipline mode.")
    ap.add_argument("--journal", choices=sorted(OA_JOURNALS),
                    help="Single-journal mode (use with --discipline).")
    ap.add_argument("--discipline", choices=sorted(DISCIPLINE_CONCEPTS),
                    help="Discipline filter (use with --journal, or alone "
                         "for any-OA-venue mode).")
    ap.add_argument("--target-count", type=int, default=1)
    ap.add_argument("--candidates-per-target", type=int, default=15,
                    help="OpenAlex candidates to fetch per target; the script "
                         "filters those with no pdf_url so overprovision.")
    ap.add_argument("--from-year", type=int, default=2018)
    ap.add_argument("--to-year", type=int, default=2026)
    ap.add_argument("-v", "--verbose", action="count", default=0,
                    help="-v INFO, -vv DEBUG")
    args = ap.parse_args()

    level = logging.WARNING
    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("vedix.oa")
    sys.exit(asyncio.run(main_async(args, log)))


if __name__ == "__main__":
    main()
