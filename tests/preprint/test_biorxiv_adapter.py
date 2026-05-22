"""§5.9 — bioRxiv preprint adapter."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from plugins.vedix.mcp.lib.orchestrator.preprint.biorxiv_adapter import (
    BIORXIV_SUBMIT_URL,
    submit_to_biorxiv,
)


def _pdf(tmp_path: Path) -> Path:
    p = tmp_path / "ms.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def _token(tmp_path: Path) -> Path:
    t = tmp_path / "biorxiv.token"
    t.write_text("biotok", encoding="utf-8")
    return t


def test_dry_run(tmp_path: Path) -> None:
    r = submit_to_biorxiv(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        credentials_path=tmp_path / "absent.token",
        dry_run=True,
    )
    assert r["status"] == "dry-run"
    assert r["target"] == "biorxiv"
    assert r["submit_url"] == BIORXIV_SUBMIT_URL


def test_missing_token_returns_error(tmp_path: Path) -> None:
    r = submit_to_biorxiv(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        credentials_path=tmp_path / "absent.token",
        dry_run=False,
    )
    assert r["status"] == "error"
    assert "token" in r["reason"].lower()


def test_success_normalises_list_metadata(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    md = {
        "title": "Title",
        "abstract": "Body",
        "authors": ["A", "B"],
        "category": "neuroscience",
    }
    fake = MagicMock(status_code=201, text="created")
    fake.json = lambda: {"submission_id": "BX-2026-00042"}
    with patch("httpx.Client.post", return_value=fake) as p:
        r = submit_to_biorxiv(
            manuscript_pdf=pdf,
            metadata=md,
            credentials_path=token,
            dry_run=False,
        )
        _, kwargs = p.call_args
        # authors list flattened to a semicolon-joined string
        assert kwargs["data"]["authors"] == "A; B"
        assert kwargs["data"]["title"] == "Title"
    assert r["status"] == "ok"
    assert r["submission_id"] == "BX-2026-00042"


def test_failure_returns_error_body(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    fake = MagicMock(status_code=413, text="payload too large")
    fake.json = lambda: {"err": "too large"}
    with patch("httpx.Client.post", return_value=fake):
        r = submit_to_biorxiv(
            manuscript_pdf=pdf,
            metadata={"title": "X"},
            credentials_path=token,
            dry_run=False,
        )
    assert r["status"] == "error"
    assert r["http_status"] == 413
