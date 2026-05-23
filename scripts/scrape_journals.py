#!/usr/bin/env python3
"""Multi-journal corpus scraper — diversifies the register-classifier
training set beyond Nature.

Where ``scrape_nature.py`` pulls one ISSN (Nature itself), this script
takes a curated queue of ``(journal, discipline, count)`` triples and
runs the same OpenAlex-discover → Anna's-fetch → pdfminer-extract
pipeline against each journal's ISSN. Output goes directly to
``~/.vedix/corpus/<discipline>/en/`` so it co-mingles with the bridged
Nature papers — the register classifier trains on the union per
discipline.

Usage::

    # Run the default 9-paper top-tier mix
    python scripts/scrape_journals.py --default-mix -v

    # Or a custom queue
    python scripts/scrape_journals.py --queue jacs:chemistry:2 cell:biology:1 -v

    # Single journal only
    python scripts/scrape_journals.py --journal science --discipline physics \
        --target-count 2 -v

Journal presets — name → ISSN (print or online, whichever OpenAlex indexes
under ``primary_location.source.issn``)::

    nature                    0028-0836
    science                   0036-8075
    cell                      0092-8674
    jacs                      0002-7863
    angewandte                1433-7851
    acs-catalysis             2155-5435
    chem-reviews              0009-2665
    plos-biology              1544-9173
    frontiers-microbiology    1664-302X
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

import httpx


async def fetch_signed_url_with_backoff(
    md5: str, *, secret_key: str, base_url: str, client: httpx.AsyncClient,
    log: logging.Logger, max_retries: int = 5,
) -> tuple[str | None, dict]:
    """Wrap fetch_annas_signed_url with exponential backoff on HTTP 429.

    Anna's fast_download.json enforces a per-burst rate limit (separate
    from the daily-quota cap). After ~10 rapid requests it returns 429
    for the next minute or two. Naive retry-now loops just amplify it.
    We sleep 30s, 60s, 120s, 240s — caps at ~8 minutes total. Any
    non-429 error or success returns immediately.
    """
    delay = 30
    for attempt in range(max_retries):
        signed_url, quota = await fetch_annas_signed_url(
            md5, secret_key=secret_key, base_url=base_url, client=client, log=log,
        )
        if signed_url is not None:
            return signed_url, quota
        # No URL means either 429, 400, or the API didn't grant. Without
        # access to the raw response inside the helper we can't easily
        # distinguish, but 429 is by far the dominant case at this stage.
        # Sleep and retry up to max_retries.
        if attempt < max_retries - 1:
            log.info("  no signed_url (likely 429) — backoff %ds then retry %d/%d",
                     delay, attempt + 2, max_retries)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 240)
    return None, {}

# Reuse the canonical helpers — the only thing that differs across
# journals is the ISSN passed to the OpenAlex filter and the output dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_nature import (  # noqa: E402 — must be after sys.path tweak
    USER_AGENT,
    extract_text,
    fetch_annas_signed_url,
    resolve_annas_md5,
    stream_pdf,
    _signed_url_matches_doi,
)


JOURNAL_PRESETS: dict[str, dict[str, str]] = {
    # name : { issn, full_name }
    "nature":                 {"issn": "0028-0836", "full_name": "Nature"},
    "science":                {"issn": "0036-8075", "full_name": "Science"},
    "cell":                   {"issn": "0092-8674", "full_name": "Cell"},
    "jacs":                   {"issn": "0002-7863", "full_name": "Journal of the American Chemical Society"},
    "angewandte":             {"issn": "1433-7851", "full_name": "Angewandte Chemie International Edition"},
    "acs-catalysis":          {"issn": "2155-5435", "full_name": "ACS Catalysis"},
    "chem-reviews":           {"issn": "0009-2665", "full_name": "Chemical Reviews"},
    "plos-biology":           {"issn": "1544-9173", "full_name": "PLoS Biology"},
    "frontiers-microbiology": {"issn": "1664-302X", "full_name": "Frontiers in Microbiology"},
}


# Curated 9-paper queue spending the remaining day quota across top-tier
# journals chosen to diversify the register classifier's training set.
#
# Layout: (journal_preset, discipline, target_count)
DEFAULT_MIX: list[tuple[str, str, int]] = [
    # Chemistry breadth — three flagship venues each with a different
    # register profile (JACS = communication-heavy, Angewandte = European
    # English, Chem Reviews = review register).
    ("jacs",                   "chemistry", 1),
    ("angewandte",             "chemistry", 1),
    ("chem-reviews",           "chemistry", 1),
    # Biology breadth — Cell (US tier-1), PLoS (open access tier-1),
    # Frontiers (mid-tier open access — useful negative for the
    # classifier since Frontiers register is looser than Cell).
    ("cell",                   "biology",   1),
    ("plos-biology",           "biology",   1),
    ("frontiers-microbiology", "biology",   1),
    # Science covers all domains; pull one each from physics, medicine,
    # and computer-science to broaden cross-discipline coverage.
    ("science",                "physics",   1),
    ("science",                "medicine",  1),
    ("science",                "computer_science", 1),
]


NICHES_CONCEPTS: dict[str, str] = {
    "chemistry":        "C185592680",
    "physics":          "C121332964",
    "biology":          "C86803240",
    "medicine":         "C71924100",
    "computer_science": "C41008148",
    "materials":        "C192562407",
    "geology":          "C127313418",
}


async def fetch_openalex_journal_dois(
    *, issn: str, target: int, candidates: int, email: str,
    from_year: int, to_year: int | None,
    concept_id: str | None,
    log: logging.Logger,
) -> list[dict]:
    """Query OpenAlex for top-cited papers from a single journal (by ISSN).

    Filters identical to ``scrape_nature.fetch_openalex_nature_dois`` but
    the ISSN is now a parameter instead of the Nature constant.
    """
    filter_parts = [
        f"primary_location.source.issn:{issn}",
        "type:article",
        "language:en",
        f"from_publication_date:{from_year}-01-01",
    ]
    if to_year is not None:
        filter_parts.append(f"to_publication_date:{to_year}-12-31")
    if concept_id is not None:
        filter_parts.append(f"concepts.id:{concept_id}")

    params = {
        "filter": ",".join(filter_parts),
        "per_page": min(candidates, 200),
        "sort": "cited_by_count:desc",
        "mailto": email,
    }
    log.info(
        "OpenAlex query: ISSN=%s lang=en from=%s%s%s candidates=%d (target %d)",
        issn, from_year,
        f" to={to_year}" if to_year else "",
        f" concept={concept_id}" if concept_id else "",
        candidates, target,
    )
    async with httpx.AsyncClient(
        timeout=60, follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
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
        works.append({
            "doi": doi,
            "title": (w.get("title") or "").strip(),
            "year": w.get("publication_year"),
            "cited_by_count": int(w.get("cited_by_count", 0)),
            "openalex_id": w.get("id"),
            "primary_concept": (
                w.get("primary_topic", {}).get("display_name")
                if isinstance(w.get("primary_topic"), dict) else None
            ),
        })
    return works


async def scrape_one_target(
    *, journal: str, discipline: str, target_count: int,
    candidates: int, from_year: int, to_year: int,
    email: str, secret_key: str, base_url: str,
    log: logging.Logger,
) -> tuple[int, int]:
    """Scrape ``target_count`` papers from one (journal, discipline) pair.

    Returns ``(downloaded_count, extracted_count)``.
    """
    preset = JOURNAL_PRESETS[journal]
    issn = preset["issn"]
    journal_label = preset["full_name"]
    concept_id = NICHES_CONCEPTS.get(discipline)

    out_root = Path(os.path.expanduser(f"~/.vedix/corpus/{discipline}/en"))
    pdf_dir = out_root / "pdf"
    text_dir = out_root / "text"
    out_root.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(exist_ok=True)
    text_dir.mkdir(exist_ok=True)

    log.info("=" * 60)
    log.info("=== %s -> %s (target %d papers)", journal_label, discipline, target_count)
    log.info("=" * 60)

    works = await fetch_openalex_journal_dois(
        issn=issn, target=target_count, candidates=candidates, email=email,
        from_year=from_year, to_year=to_year, concept_id=concept_id, log=log,
    )
    if not works:
        log.warning("OpenAlex returned 0 works for %s/%s", journal, discipline)
        return 0, 0

    # Append discovered DOIs to the acquisition manifest so they're auditable.
    acq_path = out_root / "acquisition.jsonl"
    with acq_path.open("a", encoding="utf-8") as f:
        for w in works:
            entry = dict(w)
            entry["source_journal"] = journal
            f.write(json.dumps(entry) + "\n")

    downloaded: list[dict] = []
    async with httpx.AsyncClient(
        timeout=120, follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        for i, w in enumerate(works, start=1):
            if len(downloaded) >= target_count:
                break
            title_snippet = w["title"][:80] + ("..." if len(w["title"]) > 80 else "")
            log.info("[%d/%d] cited=%d DOI=%s title=%r",
                     i, len(works), w["cited_by_count"], w["doi"], title_snippet)

            md5 = await resolve_annas_md5(
                w["doi"], w["title"],
                base_url=base_url, client=client, log=log,
            )
            if not md5:
                continue
            w["md5"] = md5

            dest_pdf = pdf_dir / f"{md5}.pdf"
            if dest_pdf.exists() and dest_pdf.stat().st_size > 1024 \
                    and dest_pdf.read_bytes()[:5] == b"%PDF-":
                log.info("  cache-hit pdf=%s", dest_pdf.name)
                downloaded.append(w)
                continue

            signed_url, quota = await fetch_signed_url_with_backoff(
                md5, secret_key=secret_key, base_url=base_url, client=client, log=log,
            )
            if quota:
                log.info(
                    "  annas quota: done_today=%s left=%s per_day=%s",
                    quota.get("downloads_done_today"),
                    quota.get("downloads_left"),
                    quota.get("downloads_per_day"),
                )
            if not signed_url:
                continue
            if not _signed_url_matches_doi(signed_url, w["doi"]):
                log.warning("  doi mismatch in signed URL — skipping")
                continue
            if await stream_pdf(signed_url, dest_pdf, client=client, log=log):
                log.info("  ok -> %s (%dKB)", dest_pdf.name, dest_pdf.stat().st_size // 1024)
                downloaded.append(w)

    log.info("=== %s/%s result: %d/%d papers downloaded ===",
             journal, discipline, len(downloaded), target_count)

    # Text extraction
    extracted = 0
    for w in downloaded:
        pdf = pdf_dir / f"{w['md5']}.pdf"
        txt = text_dir / f"{w['md5']}.txt"
        if not pdf.exists():
            continue
        if await extract_text(pdf, txt, log):
            extracted += 1

    # Append journal-tagged manifest entries so the corpus tracks provenance.
    dl_path = out_root / "downloaded.jsonl"
    with dl_path.open("a", encoding="utf-8") as f:
        for w in downloaded:
            entry = dict(w)
            entry["source_journal"] = journal
            f.write(json.dumps(entry) + "\n")

    return len(downloaded), extracted


async def main_async(args, log: logging.Logger) -> int:
    email = os.environ.get("OPENALEX_EMAIL", "").strip()
    secret_key = os.environ.get("ANNAS_SECRET_KEY", "").strip()
    if not email:
        log.error("OPENALEX_EMAIL not set in environment")
        return 1
    if not secret_key:
        log.error("ANNAS_SECRET_KEY not set in environment")
        return 1

    base_url = os.environ.get("ANNAS_BASE_URL", "https://annas-archive.org").rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    # Decide the queue.
    queue: list[tuple[str, str, int]]
    if args.default_mix:
        queue = list(DEFAULT_MIX)
    elif args.queue:
        queue = []
        for spec in args.queue:
            parts = spec.split(":")
            if len(parts) != 3:
                log.error("bad --queue spec %r; expected journal:discipline:count", spec)
                return 2
            j, d, n = parts
            if j not in JOURNAL_PRESETS:
                log.error("unknown journal %r; choose from %s", j, sorted(JOURNAL_PRESETS))
                return 2
            queue.append((j, d, int(n)))
    elif args.journal and args.discipline:
        queue = [(args.journal, args.discipline, args.target_count)]
    else:
        log.error("specify --default-mix, --queue, or --journal+--discipline")
        return 2

    # Stage 1: enumerate targets so the user sees the plan up front.
    log.info("=" * 60)
    log.info("Multi-journal corpus scrape — %d targets queued", len(queue))
    for j, d, n in queue:
        log.info("  %-25s -> %-18s x %d", JOURNAL_PRESETS[j]["full_name"], d, n)
    log.info("=" * 60)

    # Stage 2: run each target sequentially.
    totals_dl, totals_extract = 0, 0
    for j, d, n in queue:
        try:
            dl, ex = await scrape_one_target(
                journal=j, discipline=d, target_count=n,
                candidates=args.candidates_per_target,
                from_year=args.from_year, to_year=args.to_year,
                email=email, secret_key=secret_key, base_url=base_url,
                log=log,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("target %s/%s failed: %s", j, d, exc)
            continue
        totals_dl += dl
        totals_extract += ex

    print()
    print("Multi-journal corpus build summary")
    print("-" * 60)
    print(f"  targets:   {len(queue)}")
    print(f"  downloaded: {totals_dl}")
    print(f"  extracted:  {totals_extract}")
    print()
    print("Next: python scripts/prepare_corpus.py --only-pair <discipline>:en -v")
    print()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--default-mix", action="store_true",
                    help="Run the curated 9-paper mix across top-tier journals.")
    ap.add_argument("--queue", nargs="*",
                    help="Custom queue: journal:discipline:count triples, e.g. "
                         "'jacs:chemistry:2 cell:biology:1'.")
    ap.add_argument("--journal", choices=sorted(JOURNAL_PRESETS),
                    help="Single-journal mode (use with --discipline).")
    ap.add_argument("--discipline", choices=sorted(NICHES_CONCEPTS),
                    help="Discipline filter (use with --journal).")
    ap.add_argument("--target-count", type=int, default=1,
                    help="Papers per (journal, discipline) target.")
    ap.add_argument("--candidates-per-target", type=int, default=8,
                    help="OpenAlex candidates to fetch per target "
                         "(overprovision for Anna's miss rate).")
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
    log = logging.getLogger("vedix.journals")
    sys.exit(asyncio.run(main_async(args, log)))


if __name__ == "__main__":
    main()
