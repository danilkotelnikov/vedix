"""§5.9 Pre-print auto-submission CLI scaffolding.

Vedix can deposit a finished manuscript directly to arXiv, bioRxiv, OSF
or SSRN. Per-target API integration lands in Block 11; this module
covers the validation / dry-run surface that the CLI binds to today.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

VALID_TARGETS: set[str] = {"arxiv", "biorxiv", "osf", "ssrn"}


def submit(
    *,
    target: str,
    manuscript_pdf: Path,
    metadata: dict[str, Any],
    dry_run: bool = True,
) -> dict[str, Any]:
    """Validate a pre-print submission request.

    Args:
        target: One of {arxiv, biorxiv, osf, ssrn}.
        manuscript_pdf: Path to the manuscript PDF.
        metadata: Submission metadata (title, authors, abstract, …).
        dry_run: If True (default) skip the upload and return a preview.

    Returns:
        dict describing the result. `status` is one of:
        - `dry-run` — validation passed, no API call made.
        - `not_implemented` — real submission needs Block 11.
        - `error` — request was invalid.
    """
    if target not in VALID_TARGETS:
        return {
            "status": "error",
            "reason": f"unsupported target {target!r}",
            "valid_targets": sorted(VALID_TARGETS),
        }
    if not manuscript_pdf.exists():
        return {
            "status": "error",
            "reason": f"manuscript PDF not found at {manuscript_pdf}",
        }
    if dry_run:
        return {
            "status": "dry-run",
            "target": target,
            "would_submit": str(manuscript_pdf),
            "metadata_keys": sorted(metadata.keys()),
        }
    return {
        "status": "not_implemented",
        "note": "use Block 11's full implementation",
    }
