"""SWORD v2 institutional-repository adapter (§5.9).

The SWORD (Simple Web-service Offering Repository Deposit) protocol is
the lingua franca for OAI-PMH-style institutional repositories
(DSpace, EPrints, Eprints, …). Vedix submits a single PDF payload with
Basic auth, ``Content-Type: application/pdf`` and a ``Slug`` header
that carries the manuscript title; the server returns a 201 with a
``Location`` header pointing at the new deposit.

Credentials come in as ``username`` + ``password`` keyword arguments
(rather than a token file) because SWORD's auth is HTTP Basic and
multi-tenant — the same Vedix install may deposit into several
repositories at the same time. The dispatcher in
``hooks/preprint_submit.py`` lifts these from the per-target token
file when the user has saved them there.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx


def submit_to_sword(
    *,
    manuscript_pdf: Path,
    metadata: dict[str, Any],
    sword_endpoint: str,
    username: str,
    password: str,
    dry_run: bool = True,
    timeout_seconds: float = 120.0,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Deposit a PDF into a SWORD v2 institutional repository.

    Args:
        manuscript_pdf: Path to the PDF blob.
        metadata: ``title``, ``in_progress`` (bool — leaves deposit
            in-progress so the user can edit metadata in their IR
            backend), ``packaging`` (e.g. ``"http://purl.org/net/sword/package/Binary"``).
        sword_endpoint: Collection URL (the IR-specific deposit URL).
        username: HTTP Basic username.
        password: HTTP Basic password.
        dry_run: Skip the upload and return a preview.
        extra_headers: Extra headers to merge into the request (some
            IRs require ``On-Behalf-Of`` for sword-mediated deposit).
    """
    if dry_run:
        return {
            "status": "dry-run",
            "target": "sword",
            "endpoint": sword_endpoint,
            "would_submit_pdf": str(manuscript_pdf),
            "metadata": metadata,
        }
    if not manuscript_pdf.exists():
        return {
            "status": "error",
            "target": "sword",
            "reason": f"manuscript PDF missing at {manuscript_pdf}",
        }
    auth = base64.b64encode(
        f"{username}:{password}".encode("utf-8")
    ).decode("ascii")
    headers: dict[str, str] = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=manuscript.pdf",
        "Slug": str(metadata.get("title", "manuscript")),
        "Packaging": str(
            metadata.get(
                "packaging",
                "http://purl.org/net/sword/package/Binary",
            )
        ),
        "In-Progress": "true" if metadata.get("in_progress") else "false",
    }
    if extra_headers:
        headers.update(extra_headers)
    with httpx.Client(timeout=timeout_seconds) as client:
        with manuscript_pdf.open("rb") as f:
            response = client.post(
                sword_endpoint,
                headers=headers,
                content=f.read(),
            )
    if response.status_code in (200, 201, 202):
        return {
            "status": "ok",
            "target": "sword",
            "endpoint": sword_endpoint,
            "http_status": response.status_code,
            "deposit_url": response.headers.get("Location"),
        }
    return {
        "status": "error",
        "target": "sword",
        "endpoint": sword_endpoint,
        "http_status": response.status_code,
        "body": response.text[:500],
    }
