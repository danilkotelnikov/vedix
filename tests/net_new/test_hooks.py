"""Smoke tests for the B9/B10/B11 hook scaffolding (§5.7, §5.8, §5.9)."""
from __future__ import annotations

from plugins.vedix.mcp.lib.orchestrator.hooks import (
    ide_protocol,
    preprint_submit,
    webui_events,
)


# §5.7 — SSE event bus
def test_event_bus_emits_and_streams():
    bus = webui_events.EventBus(max_buffer=10)
    id0 = bus.emit(kind="phase.start", payload={"phase": "ideation"})
    id1 = bus.emit(kind="phase.start", payload={"phase": "literature"})
    frames = list(bus.stream(since_id=-1))
    assert len(frames) == 2
    assert "phase.start" in frames[0]
    # Stream from after the first event yields only the second.
    frames_after = list(bus.stream(since_id=id0))
    assert len(frames_after) == 1
    assert str(id1) in frames_after[0]


def test_event_bus_module_singletons_share_state():
    before = len(list(webui_events.stream(since_id=-1)))
    webui_events.emit("test.kind", {"k": "v"})
    after = len(list(webui_events.stream(since_id=-1)))
    assert after == before + 1


# §5.8 — IDE JSON-RPC
def test_ide_handle_known_method():
    req = ide_protocol.IDERequest(method="job.status", params={"job_id": "x"}, id=7)
    resp = ide_protocol.handle(req)
    assert resp.error is None
    assert resp.id == 7
    assert resp.result is not None
    assert resp.result["method"] == "job.status"


def test_ide_handle_unknown_method():
    req = ide_protocol.IDERequest(method="job.warp", params={}, id=1)
    resp = ide_protocol.handle(req)
    assert resp.result is None
    assert resp.error is not None
    assert resp.error["code"] == -32601


# §5.9 — pre-print submit
def test_preprint_submit_dry_run(tmp_path):
    pdf = tmp_path / "manuscript.pdf"
    pdf.write_bytes(b"%PDF-1.4 dummy")
    out = preprint_submit.submit(
        target="arxiv",
        manuscript_pdf=pdf,
        metadata={"title": "T", "authors": ["A"], "abstract": "ab"},
        dry_run=True,
    )
    assert out["status"] == "dry-run"
    assert out["target"] == "arxiv"


def test_preprint_submit_bad_target(tmp_path):
    pdf = tmp_path / "manuscript.pdf"
    pdf.write_bytes(b"")
    out = preprint_submit.submit(
        target="not-a-server",
        manuscript_pdf=pdf,
        metadata={},
        dry_run=True,
    )
    assert out["status"] == "error"
    assert "unsupported" in out["reason"]


def test_preprint_submit_missing_pdf(tmp_path):
    out = preprint_submit.submit(
        target="biorxiv",
        manuscript_pdf=tmp_path / "missing.pdf",
        metadata={},
        dry_run=True,
    )
    assert out["status"] == "error"
    assert "not found" in out["reason"]
