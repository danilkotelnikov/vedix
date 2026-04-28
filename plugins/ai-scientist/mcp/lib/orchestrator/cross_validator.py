"""Strict literature cross-validator. Per spec §4.

Stage 1: DOI gate (hard) — Crossref/DataCite resolve + fuzzy title match.
Stage 2: enrichment cascade (soft) — OpenAlex/S2/Consensus/Anna's OA-only/PubMed.
Stage 3: claim support (optional) — top-cited papers only.
"""
from __future__ import annotations
import re
import time
from typing import Optional

import httpx

DOI_REGEX = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")
TITLE_FUZZY_THRESHOLD = 0.85


def normalize_doi(raw: str) -> str:
    """Strip url prefix / doi: prefix; lowercase; strip whitespace."""
    s = (raw or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s


def _crossref_resolve(doi: str, email: str, timeout: float = 10.0) -> Optional[dict]:
    """Polite-pool Crossref resolve. Returns message dict or None."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": f"ai-scientist-plugin/2.1 (mailto:{email})"}
    try:
        r = httpx.get(url, headers=headers, timeout=timeout,
                      params={"mailto": email})
    except (httpx.RequestError, httpx.TimeoutException):
        return None
    if r.status_code == 200:
        return r.json().get("message") or {}
    return None


def _datacite_resolves(doi: str, timeout: float = 10.0) -> Optional[dict]:
    """DataCite fallback for non-Crossref DOIs."""
    url = f"https://api.datacite.org/dois/{doi}"
    try:
        r = httpx.get(url, timeout=timeout)
    except (httpx.RequestError, httpx.TimeoutException):
        return None
    if r.status_code == 200:
        attrs = r.json().get("data", {}).get("attributes", {})
        return {"title": [attrs.get("titles", [{}])[0].get("title", "")],
                "author": attrs.get("creators", []),
                "issued": {"date-parts": [[attrs.get("publicationYear")]]}}
    return None


def _fuzzy_title_match(a: str, b: str) -> float:
    """Token-sort-ratio normalized to [0, 1]."""
    try:
        from rapidfuzz.fuzz import token_sort_ratio
    except ImportError:
        # Fallback: lowercased equality
        return 1.0 if a.lower().strip() == b.lower().strip() else 0.0
    return token_sort_ratio(a, b) / 100.0


def stage1_doi_gate(paper: dict, *, harvest_title: str,
                    crossref_email: str) -> dict:
    """Stage 1 — strict DOI gate. Returns dict with passed: bool."""
    raw = paper.get("doi", "")
    doi = normalize_doi(raw)
    if not doi or not DOI_REGEX.match(doi):
        return {"passed": False, "reason": "no_doi"}
    cr = _crossref_resolve(doi, email=crossref_email)
    registry_data = cr
    if cr is None:
        # Try DataCite (datasets, preprints)
        dc = _datacite_resolves(doi)
        if dc is None:
            return {"passed": False, "reason": "doi_404_both_registries"}
        registry_data = dc
    registry_title = ""
    titles = registry_data.get("title", [])
    if isinstance(titles, list) and titles:
        registry_title = titles[0]
    score = _fuzzy_title_match(harvest_title, registry_title)
    if score < TITLE_FUZZY_THRESHOLD:
        return {"passed": False,
                "reason": f"title_mismatch_{score:.2f}",
                "registry_title": registry_title,
                "harvest_title": harvest_title}
    return {"passed": True, "doi": doi, "title_score": score,
            "registry_data": registry_data}
