"""§5.9 — SWORD v2 institutional-repository adapter."""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

from plugins.vedix.mcp.lib.orchestrator.preprint.sword_adapter import (
    submit_to_sword,
)


def _pdf(tmp_path: Path) -> Path:
    p = tmp_path / "ms.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def test_dry_run(tmp_path: Path) -> None:
    r = submit_to_sword(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        sword_endpoint="https://ir.example.edu/swordv2/collection/1",
        username="u",
        password="p",
        dry_run=True,
    )
    assert r["status"] == "dry-run"
    assert r["target"] == "sword"
    assert r["endpoint"] == "https://ir.example.edu/swordv2/collection/1"


def test_missing_pdf_returns_error(tmp_path: Path) -> None:
    r = submit_to_sword(
        manuscript_pdf=tmp_path / "ghost.pdf",
        metadata={"title": "X"},
        sword_endpoint="https://ir.example.edu/swordv2/collection/1",
        username="u",
        password="p",
        dry_run=False,
    )
    assert r["status"] == "error"
    assert "pdf" in r["reason"].lower()


def test_success_returns_deposit_url(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    fake = MagicMock(
        status_code=201,
        text="created",
        headers={"Location": "https://ir.example.edu/deposits/42"},
    )
    with patch("httpx.Client.post", return_value=fake) as p:
        r = submit_to_sword(
            manuscript_pdf=pdf,
            metadata={"title": "Some Paper", "in_progress": True},
            sword_endpoint="https://ir.example.edu/swordv2/collection/1",
            username="alice",
            password="s3cret",
            dry_run=False,
        )
        _, kwargs = p.call_args
        expected_auth = "Basic " + base64.b64encode(
            b"alice:s3cret"
        ).decode("ascii")
        assert kwargs["headers"]["Authorization"] == expected_auth
        assert kwargs["headers"]["Content-Type"] == "application/pdf"
        assert kwargs["headers"]["Slug"] == "Some Paper"
        assert kwargs["headers"]["In-Progress"] == "true"
    assert r["status"] == "ok"
    assert r["deposit_url"] == "https://ir.example.edu/deposits/42"


def test_failure_returns_error_body(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    fake = MagicMock(status_code=401, text="auth failed", headers={})
    with patch("httpx.Client.post", return_value=fake):
        r = submit_to_sword(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            sword_endpoint="https://ir.example.edu/swordv2/collection/1",
            username="alice",
            password="wrong",
            dry_run=False,
        )
    assert r["status"] == "error"
    assert r["http_status"] == 401


def test_extra_headers_are_merged(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    fake = MagicMock(
        status_code=201, text="ok", headers={"Location": "http://x/y"}
    )
    with patch("httpx.Client.post", return_value=fake) as p:
        submit_to_sword(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            sword_endpoint="https://ir.example.edu/swordv2/collection/1",
            username="u",
            password="p",
            dry_run=False,
            extra_headers={"On-Behalf-Of": "agent@example.com"},
        )
        _, kwargs = p.call_args
        assert (
            kwargs["headers"]["On-Behalf-Of"] == "agent@example.com"
        )


def test_in_progress_defaults_to_false(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    fake = MagicMock(status_code=201, text="ok", headers={})
    with patch("httpx.Client.post", return_value=fake) as p:
        submit_to_sword(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            sword_endpoint="https://ir.example.edu/swordv2/collection/1",
            username="u",
            password="p",
            dry_run=False,
        )
        _, kwargs = p.call_args
        assert kwargs["headers"]["In-Progress"] == "false"
