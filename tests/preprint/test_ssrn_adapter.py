"""§5.9 — SSRN preprint adapter (deep-link only — no public API)."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from plugins.vedix.mcp.lib.orchestrator.preprint.ssrn_adapter import (
    SSRN_SUBMIT_URL_BASE,
    submit_to_ssrn,
)


def _pdf(tmp_path: Path) -> Path:
    p = tmp_path / "ms.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def test_dry_run(tmp_path: Path) -> None:
    r = submit_to_ssrn(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        dry_run=True,
    )
    assert r["status"] == "dry-run"


def test_returns_manual_redirect_with_prefilled_url(tmp_path: Path) -> None:
    md = {
        "title": "An Empirical Study",
        "abstract": "We find that …",
        "authors": ["Jane Doe", "John Doe"],
        "tags": ["macro", "finance"],
        "classifications": ["E50", "G12"],
    }
    r = submit_to_ssrn(
        manuscript_pdf=_pdf(tmp_path),
        metadata=md,
        dry_run=False,
    )
    assert r["status"] == "manual-redirect"
    assert r["target"] == "ssrn"
    parsed = urlparse(r["open_in_browser"])
    assert parsed.scheme == "https"
    assert parsed.netloc == "papers.ssrn.com"
    qs = parse_qs(parsed.query)
    assert qs["title"][0] == "An Empirical Study"
    assert qs["authors"][0] == "Jane Doe; John Doe"
    assert qs["keywords"][0] == "macro,finance"
    assert qs["jel"][0] == "E50,G12"


def test_credentials_path_is_ignored(tmp_path: Path) -> None:
    """SSRN has no API — passing a token path must not change behaviour."""
    r = submit_to_ssrn(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        credentials_path=tmp_path / "any.token",
        dry_run=False,
    )
    assert r["status"] == "manual-redirect"
    assert r["target"] == "ssrn"


def test_custom_submit_url_base(tmp_path: Path) -> None:
    r = submit_to_ssrn(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        dry_run=False,
        submit_url_base="https://custom.example.com/submit/",
    )
    assert r["open_in_browser"].startswith(
        "https://custom.example.com/submit/?"
    )


def test_url_base_default_matches_module_constant() -> None:
    assert SSRN_SUBMIT_URL_BASE.startswith("https://papers.ssrn.com")
