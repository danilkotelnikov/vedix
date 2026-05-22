"""Stage 1 — harvest paper candidates via MCPs.

Fans out one query per (discipline keyword × MCP) and merges the results
into a deduplicated JSONL of candidates with an open-licence filter. The
six ``_call_*`` helpers are stubs by design: production wires them to the
Vedix MCP layer (B6/B7); the unit tests patch them in to inject synthetic
candidates.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

# Discipline → search-keyword routing. Each keyword becomes a separate MCP
# query so we exercise multiple facets of the field rather than a single
# stale phrase.
DISCIPLINE_QUERIES: dict[str, list[str]] = {
    "chemistry": [
        "organic synthesis",
        "catalysis",
        "spectroscopy",
        "reaction kinetics",
        "crystallography",
    ],
    "biology": [
        "gene expression",
        "protein structure",
        "cell signaling",
        "microbiome",
        "evolutionary biology",
    ],
    "medicine": [
        "randomized clinical trial",
        "epidemiology",
        "biomarker",
        "therapeutic intervention",
        "diagnostic accuracy",
    ],
    "physics": [
        "quantum mechanics",
        "condensed matter",
        "particle physics",
        "general relativity",
        "thermodynamics",
    ],
    "mathematics": [
        "topology",
        "algebraic geometry",
        "stochastic processes",
        "graph theory",
        "functional analysis",
    ],
    "geology": [
        "plate tectonics",
        "geochronology",
        "stratigraphy",
        "geochemistry",
        "volcanology",
    ],
    "computer_science": [
        "machine learning",
        "distributed systems",
        "type theory",
        "computational complexity",
        "computer vision",
    ],
    "humanities": [
        "literary analysis",
        "historical methodology",
        "philosophical argument",
        "linguistic semantics",
        "cultural studies",
    ],
}

# Hints passed verbatim to MCP backends that accept a language qualifier.
LANG_HINTS: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "zh": "Chinese",
    "ja": "Japanese",
}

# Open-licence prefixes we consider redistributable for training. Anything
# else (all-rights-reserved, restricted, paywalled) is rejected.
_OPEN_LICENCE_PREFIXES = ("cc", "public", "open", "mit", "apache")


# --------------------------------------------------------------------------- #
# MCP call stubs. Production routes these through                              #
# plugins/vedix/mcp/lib/orchestrator/mcp_client.py (B6/B7).                    #
# Tests patch them via unittest.mock.AsyncMock.                                #
# --------------------------------------------------------------------------- #
async def _call_openalex(query: str, language: str, n: int) -> list[dict]:
    """Search OpenAlex via ``mcp__openalex__search_works``."""
    return []


async def _call_semanticscholar(query: str, language: str, n: int) -> list[dict]:
    """Search via ``mcp__semanticscholar__search_semantic_scholar``."""
    return []


async def _call_arxiv(query: str, language: str, n: int) -> list[dict]:
    """Search via ``mcp__arxiv__search_papers``."""
    return []


async def _call_biorxiv(query: str, language: str, n: int) -> list[dict]:
    """Search via ``mcp__bio-research:biorxiv search_preprints``."""
    return []


async def _call_pubmed(query: str, language: str, n: int) -> list[dict]:
    """Search via ``mcp__pubmed__search_articles``."""
    return []


async def _call_annas(query: str, language: str, n: int) -> list[dict]:
    """Search Anna's Archive via the ``annas-mcp`` stdio server.

    Spawns ``npx -y annas-mcp mcp`` as a subprocess (using the user's
    ANNAS_SECRET_KEY / ANNAS_BASE_URL / ANNAS_DOWNLOAD_PATH env vars), calls
    the ``article_search`` tool, and normalizes the JSON payload into the
    Vedix candidate shape ``{id, doi, title, year, language, license,
    full_text_url, _source}``.

    Returns an empty list when ANNAS_SECRET_KEY is unset (silent skip so
    parallel harvest from other MCPs is unaffected).
    """
    import logging
    import os
    from pathlib import Path

    log = logging.getLogger("vedix.acquisition.annas")
    secret_key = os.environ.get("ANNAS_SECRET_KEY", "").strip()
    if not secret_key:
        log.debug("ANNAS_SECRET_KEY not set; skipping Anna's Archive (set it to enable; 100 papers/day quota applies)")
        return []

    base_url = os.environ.get("ANNAS_BASE_URL", "https://annas-archive.org")
    download_path = os.environ.get(
        "ANNAS_DOWNLOAD_PATH",
        str(Path.home() / ".vedix" / "raw_downloads"),
    )
    Path(download_path).mkdir(parents=True, exist_ok=True)

    from .mcp_client import MCPClient, extract_text_from_mcp_result

    log.info("annas-mcp search: query=%r language=%s limit=%d", query, language, n)

    try:
        async with MCPClient(
            command="npx",
            args=["-y", "annas-mcp", "mcp"],
            env={
                "ANNAS_SECRET_KEY": secret_key,
                "ANNAS_BASE_URL": base_url,
                "ANNAS_DOWNLOAD_PATH": download_path,
            },
        ) as client:
            result = await client.call_tool(
                "article_search",
                {"query": query, "language": language, "limit": n},
                timeout=120.0,
            )
    except Exception as exc:  # noqa: BLE001 — never let one MCP nuke the whole harvest
        log.warning("annas-mcp call failed: %s", exc)
        return []

    text = extract_text_from_mcp_result(result)
    if not text:
        log.warning("annas-mcp returned no text payload for query=%r", query)
        return []

    # The server may return JSON directly, or JSON wrapped in a string. Try both.
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        log.warning("annas-mcp returned non-JSON for query=%r (first 200 chars: %r)", query, text[:200])
        return []
    if isinstance(payload, dict):
        items = payload.get("results") or payload.get("articles") or payload.get("items") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    normalized: list[dict] = []
    for paper in items[:n]:
        if not isinstance(paper, dict):
            continue
        # Anna's Archive identifies papers by md5; fall back to DOI when present.
        ident = paper.get("md5") or paper.get("doi") or paper.get("id")
        if not ident:
            continue
        # Construct a download URL. annas-mcp may emit a ready-to-fetch URL;
        # otherwise build one from md5.
        download_url = (
            paper.get("download_url")
            or paper.get("url")
            or (f"{base_url.rstrip('/')}/md5/{paper['md5']}" if paper.get("md5") else None)
        )
        if not download_url:
            continue
        normalized.append({
            "id": ident,
            "doi": paper.get("doi"),
            "title": (paper.get("title") or "").strip(),
            "year": paper.get("year") or paper.get("publication_year"),
            "language": paper.get("language", language),
            "license": paper.get("license", "annas-archive"),
            "full_text_url": download_url,
            "venue": paper.get("journal") or paper.get("venue"),
            "_source": "annas",
        })
    log.info("annas-mcp returned %d candidates for query=%r", len(normalized), query)
    return normalized


# --------------------------------------------------------------------------- #
# Public entry point                                                           #
# --------------------------------------------------------------------------- #
async def harvest(
    *,
    discipline: str,
    language: str,
    target_count: int = 200,
    out_path: Path,
) -> list[dict]:
    """Harvest up to ``target_count`` candidate papers for the pair.

    Fans queries out across all configured MCPs in parallel, deduplicates
    by DOI/id, applies the open-licence and language filters, then writes
    the survivors to ``out_path`` as JSONL.

    Returns the in-memory candidate list (also flushed to disk).
    """
    queries = DISCIPLINE_QUERIES.get(discipline, [discipline])
    per_query = max(10, target_count // max(1, len(queries)))

    tasks: list = []
    for q in queries:
        tasks.append(_call_openalex(q, language, per_query))
        tasks.append(_call_semanticscholar(q, language, per_query))
        tasks.append(_call_arxiv(q, language, per_query))
        if discipline in ("biology", "medicine"):
            tasks.append(_call_biorxiv(q, language, per_query))
            tasks.append(_call_pubmed(q, language, per_query))
        tasks.append(_call_annas(q, language, per_query))

    results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    candidates: list[dict] = []
    seen_dois: set[str] = set()
    for lst in results_lists:
        if isinstance(lst, BaseException):
            # Failures from any single MCP shouldn't abort the harvest.
            continue
        for paper in lst:
            doi = paper.get("doi") or paper.get("id")
            if not doi or doi in seen_dois:
                continue
            licence = str(paper.get("license", "")).lower()
            if not licence.startswith(_OPEN_LICENCE_PREFIXES):
                continue
            paper_lang = paper.get("language")
            if paper_lang and paper_lang[:2] != language:
                continue
            candidates.append(paper)
            seen_dois.add(doi)
            if len(candidates) >= target_count:
                break
        if len(candidates) >= target_count:
            break

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")
    return candidates
