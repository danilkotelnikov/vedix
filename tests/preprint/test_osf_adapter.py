"""§5.9 — OSF preprint adapter."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from plugins.vedix.mcp.lib.orchestrator.preprint.osf_adapter import submit_to_osf


def _pdf(tmp_path: Path) -> Path:
    p = tmp_path / "ms.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    return p


def _token(tmp_path: Path) -> Path:
    t = tmp_path / "osf.token"
    t.write_text("osftok", encoding="utf-8")
    return t


def test_dry_run(tmp_path: Path) -> None:
    r = submit_to_osf(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        credentials_path=tmp_path / "absent.token",
        dry_run=True,
    )
    assert r["status"] == "dry-run"
    assert r["target"] == "osf"


def test_missing_token_returns_error(tmp_path: Path) -> None:
    r = submit_to_osf(
        manuscript_pdf=_pdf(tmp_path),
        metadata={"title": "X"},
        credentials_path=tmp_path / "absent.token",
        dry_run=False,
    )
    assert r["status"] == "error"


def test_two_step_create_then_upload_success(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    create_resp = MagicMock(status_code=201, text="created")
    create_resp.json = lambda: {
        "data": {"id": "abc123", "type": "preprints"}
    }
    upload_resp = MagicMock(status_code=201, text="uploaded")
    with patch("httpx.Client.post", return_value=create_resp) as post_p, patch(
        "httpx.Client.put", return_value=upload_resp
    ) as put_p:
        r = submit_to_osf(
            manuscript_pdf=pdf,
            metadata={"title": "T", "abstract": "A", "tags": ["x"]},
            credentials_path=token,
            dry_run=False,
        )
        assert post_p.called
        assert put_p.called
        put_args, put_kwargs = put_p.call_args
        # Upload PUT to the files endpoint with the node id baked in
        assert "abc123" in put_args[0]
        assert put_kwargs["params"]["name"] == "manuscript.pdf"
    assert r["status"] == "ok"
    assert r["node_id"] == "abc123"


def test_create_node_failure_short_circuits(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    create_resp = MagicMock(status_code=403, text="forbidden")
    create_resp.json = lambda: {"err": "forbidden"}
    with patch("httpx.Client.post", return_value=create_resp), patch(
        "httpx.Client.put"
    ) as put_p:
        r = submit_to_osf(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            credentials_path=token,
            dry_run=False,
        )
        assert not put_p.called  # never reaches upload step
    assert r["status"] == "error"
    assert r["stage"] == "create_node"


def test_upload_failure_returns_error_with_node_id(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    create_resp = MagicMock(status_code=201, text="created")
    create_resp.json = lambda: {"data": {"id": "xyz789"}}
    upload_resp = MagicMock(status_code=500, text="boom")
    with patch("httpx.Client.post", return_value=create_resp), patch(
        "httpx.Client.put", return_value=upload_resp
    ):
        r = submit_to_osf(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            credentials_path=token,
            dry_run=False,
        )
    assert r["status"] == "error"
    assert r["stage"] == "upload_pdf"
    assert r["node_id"] == "xyz789"


def test_create_node_2xx_without_data_id_is_error(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path)
    token = _token(tmp_path)
    create_resp = MagicMock(status_code=200, text="weird")
    create_resp.json = lambda: {"meta": "no data block"}
    with patch("httpx.Client.post", return_value=create_resp):
        r = submit_to_osf(
            manuscript_pdf=pdf,
            metadata={"title": "T"},
            credentials_path=token,
            dry_run=False,
        )
    assert r["status"] == "error"
    assert r["stage"] == "create_node"
