"""OSF (Open Science Framework) pre-print submission adapter (§5.9).

OSF preprints land in two steps:

1. ``POST /v2/preprints/`` creates a preprint *node* (a logical record)
   with title, abstract, tags, etc. and returns ``data.id``.
2. ``PUT /v1/resources/{node_id}/providers/osfstorage/?name=…`` uploads
   the PDF blob to the OSF storage backend, attaching it to the node.

The BYOK credential is a personal access token at
``~/.vedix/byok/secrets/osf.token``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

OSF_API_BASE = "https://api.osf.io"
OSF_FILES_BASE = "https://files.osf.io"


def submit_to_osf(
    *,
    manuscript_pdf: Path,
    metadata: dict[str, Any],
    credentials_path: Path,
    dry_run: bool = True,
    api_base: str = OSF_API_BASE,
    files_base: str = OSF_FILES_BASE,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Submit a manuscript to OSF Preprints (two-step: node + upload)."""
    if dry_run:
        return {
            "status": "dry-run",
            "target": "osf",
            "would_submit_pdf": str(manuscript_pdf),
            "api_base": api_base,
            "metadata": metadata,
        }
    if not credentials_path.exists():
        return {
            "status": "error",
            "target": "osf",
            "reason": f"OSF token missing at {credentials_path}",
        }
    if not manuscript_pdf.exists():
        return {
            "status": "error",
            "target": "osf",
            "reason": f"manuscript PDF missing at {manuscript_pdf}",
        }
    token = credentials_path.read_text(encoding="utf-8").strip()
    headers = {"Authorization": f"Bearer {token}"}
    node_payload = {
        "data": {
            "type": "preprints",
            "attributes": {
                "title": metadata.get("title", ""),
                "abstract": metadata.get("abstract", ""),
                "tags": metadata.get("tags", []),
                "subjects": metadata.get("subjects", []),
            },
        }
    }
    with httpx.Client(timeout=timeout_seconds) as client:
        # Step 1: create the preprint node.
        node_resp = client.post(
            f"{api_base}/v2/preprints/",
            headers={**headers, "Content-Type": "application/vnd.api+json"},
            json=node_payload,
        )
        if node_resp.status_code not in (200, 201):
            return {
                "status": "error",
                "target": "osf",
                "stage": "create_node",
                "http_status": node_resp.status_code,
                "body": node_resp.text[:500],
            }
        try:
            node_body = node_resp.json()
        except Exception:  # pragma: no cover
            node_body = {}
        node_id = (
            node_body.get("data", {}).get("id")
            if isinstance(node_body, dict)
            else None
        )
        if not node_id:
            return {
                "status": "error",
                "target": "osf",
                "stage": "create_node",
                "reason": "OSF returned 2xx but no data.id was present",
                "response": node_body,
            }
        # Step 2: upload the PDF blob.
        with manuscript_pdf.open("rb") as f:
            upload_resp = client.put(
                f"{files_base}/v1/resources/{node_id}/providers/osfstorage/",
                headers=headers,
                params={"name": "manuscript.pdf", "kind": "file"},
                content=f.read(),
            )
    if upload_resp.status_code in (200, 201):
        return {
            "status": "ok",
            "target": "osf",
            "node_id": node_id,
            "http_status": upload_resp.status_code,
        }
    return {
        "status": "error",
        "target": "osf",
        "stage": "upload_pdf",
        "node_id": node_id,
        "http_status": upload_resp.status_code,
        "body": upload_resp.text[:500],
    }
