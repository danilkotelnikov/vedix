"""bioRxiv pre-print submission adapter (§5.9).

bioRxiv (Cold Spring Harbor) accepts authenticated submissions via a
REST API. The submission endpoint takes the PDF as a multipart upload
plus a metadata dict (title, abstract, authors, corresponding author,
license, institution …). Our credential model mirrors arXiv: a single
bearer token at ``~/.vedix/byok/secrets/biorxiv.token``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

BIORXIV_SUBMIT_URL = "https://api.biorxiv.org/submission/v1/papers"


def submit_to_biorxiv(
    *,
    manuscript_pdf: Path,
    metadata: dict[str, Any],
    credentials_path: Path,
    dry_run: bool = True,
    submit_url: str = BIORXIV_SUBMIT_URL,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Submit a manuscript to bioRxiv.

    Args:
        manuscript_pdf: Path to the final PDF.
        metadata: Submission metadata: ``title``, ``abstract``,
            ``authors`` (list[str]), ``corresponding_email``,
            ``institution``, ``license``, ``category`` …
        credentials_path: Token file (Bearer auth).
        dry_run: Skip the upload and return a preview.
    """
    if dry_run:
        return {
            "status": "dry-run",
            "target": "biorxiv",
            "would_submit_pdf": str(manuscript_pdf),
            "submit_url": submit_url,
            "metadata": metadata,
        }
    if not credentials_path.exists():
        return {
            "status": "error",
            "target": "biorxiv",
            "reason": f"bioRxiv token missing at {credentials_path}",
        }
    if not manuscript_pdf.exists():
        return {
            "status": "error",
            "target": "biorxiv",
            "reason": f"manuscript PDF missing at {manuscript_pdf}",
        }
    token = credentials_path.read_text(encoding="utf-8").strip()
    data: dict[str, str] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            data[key] = "; ".join(str(v) for v in value)
        else:
            data[key] = str(value)
    with httpx.Client(timeout=timeout_seconds) as client:
        with manuscript_pdf.open("rb") as f:
            response = client.post(
                submit_url,
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "manuscript": (
                        "manuscript.pdf",
                        f,
                        "application/pdf",
                    )
                },
                data=data,
            )
    if response.status_code in (200, 201, 202):
        try:
            body = response.json()
        except Exception:  # pragma: no cover
            body = {"raw": response.text[:500]}
        return {
            "status": "ok",
            "target": "biorxiv",
            "submission_id": body.get("submission_id")
            if isinstance(body, dict)
            else None,
            "http_status": response.status_code,
            "response": body,
        }
    return {
        "status": "error",
        "target": "biorxiv",
        "http_status": response.status_code,
        "body": response.text[:500],
    }
