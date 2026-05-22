"""SSRN pre-print submission adapter (§5.9).

SSRN does not publish an authenticated submission API. The next best
thing we can ship is a deep-linked form-fill URL: the user opens the
returned URL in a browser, the SSRN submission form is pre-populated
from the query string, and the user only has to attach the PDF and
press *Submit*.

We always return ``status="manual-redirect"`` (never ``ok``) so the
caller can render an actionable prompt instead of assuming the deposit
finished.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

SSRN_SUBMIT_URL_BASE = "https://papers.ssrn.com/sol3/submit/"


def submit_to_ssrn(
    *,
    manuscript_pdf: Path,
    metadata: dict[str, Any],
    credentials_path: Path | None = None,
    dry_run: bool = True,
    submit_url_base: str = SSRN_SUBMIT_URL_BASE,
) -> dict[str, Any]:
    """Build a pre-filled SSRN submission URL for the user to open.

    Args:
        manuscript_pdf: PDF path (returned in the payload but not
            uploaded — SSRN's web form requires a browser session).
        metadata: ``title``, ``abstract``, ``authors`` (list[str]),
            ``tags`` (list[str]), ``classifications`` (list[str], JEL
            codes for econ uploads).
        credentials_path: Unused — SSRN has no public API. Kept on the
            signature so the dispatcher in
            ``hooks/preprint_submit.py`` can call every adapter the
            same way.
        dry_run: When True, returns ``status="dry-run"`` so previews
            don't leak the deep-link URL into pipeline outputs.

    Returns:
        ``status="manual-redirect"`` with ``open_in_browser`` set to
        the deep-linked URL.
    """
    if dry_run:
        return {
            "status": "dry-run",
            "target": "ssrn",
            "would_submit_pdf": str(manuscript_pdf),
            "metadata": metadata,
        }
    params: dict[str, str] = {
        "title": metadata.get("title", ""),
        "abstract": metadata.get("abstract", ""),
        "authors": "; ".join(metadata.get("authors", [])),
        "keywords": ",".join(metadata.get("tags", [])),
    }
    classifications = metadata.get("classifications") or []
    if classifications:
        params["jel"] = ",".join(classifications)
    if metadata.get("doi"):
        params["doi"] = str(metadata["doi"])
    url = f"{submit_url_base}?{urlencode(params)}"
    return {
        "status": "manual-redirect",
        "target": "ssrn",
        "open_in_browser": url,
        "manuscript_pdf": str(manuscript_pdf),
        "note": (
            "SSRN has no public submission API. Open the URL above in "
            "your browser — the form will be pre-populated; attach the "
            "PDF manually and submit."
        ),
    }
