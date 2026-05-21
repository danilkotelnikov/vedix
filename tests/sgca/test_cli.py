import json
import pytest
import tarfile
from pathlib import Path
from plugins.vedix.mcp.lib.orchestrator.sgca.cli import (
    verify_command, rebuild_command, export_command, import_command,
    gc_command, add_paper_command,
)
from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    KGFragment, KGNodes, Claim, Author, RawPointer, Provenance,
)


def _seed_with_raw(tmp_path, scope_id, claim_quote):
    raw_dir = tmp_path / ".vedix" / "jobs" / scope_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / "p.txt"
    raw.write_text(claim_quote, encoding="utf-8")
    store = KGStore(tier=Tier.JOB, scope_id=scope_id)
    store.write_paper(KGFragment(
        paper_id="p", doi="10.1/p", title="t", year=2024,
        authors=[Author(id="author:x", name="x")], language="en", license="CC-BY",
        raw_pointer=RawPointer(text=str(raw), byte_len=len(claim_quote)),
        nodes=KGNodes(claims=[
            Claim(id="p.c1", type="empirical", paraphrase="x",
                  verbatim_quote=claim_quote, quote_byte_range=[0, len(claim_quote)],
                  page=1, section="Results", confidence=0.9, hedge=False,
                  provenance=Provenance(extractor_model="x", extractor_ts=0)),
        ]),
        edges=[],
    ))
    return store


def test_verify_passes_when_quotes_match_raw(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    _seed_with_raw(tmp_path, "job_verify_ok", "matching quote text")
    report = verify_command(tier=Tier.JOB, scope_id="job_verify_ok")
    assert report["ok"] is True
    assert report["mismatches"] == []


def test_verify_fails_on_drift(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = _seed_with_raw(tmp_path, "job_verify_drift", "claim quote")
    # Corrupt the raw file so the byte_range no longer matches
    raw = Path(store.read_paper("p").raw_pointer.text)
    raw.write_text("totally different content", encoding="utf-8")
    report = verify_command(tier=Tier.JOB, scope_id="job_verify_drift")
    assert report["ok"] is False
    assert len(report["mismatches"]) == 1
    assert report["mismatches"][0]["claim_id"] == "p.c1"


def test_export_then_import_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store_src = _seed_with_raw(tmp_path, "src", "exported")
    # Use job tier for the test
    out = tmp_path / "export_job.tgz"
    export_command(tier=Tier.JOB, scope_id="src", dest=out)
    assert out.exists()
    import_command(tier=Tier.JOB, scope_id="dst", src=out)
    store_dst = KGStore(tier=Tier.JOB, scope_id="dst")
    paper = store_dst.read_paper("p")
    assert paper is not None
    assert paper.nodes.claims[0].verbatim_quote == "exported"


def test_gc_removes_old_wings(tmp_path, monkeypatch):
    import time
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = _seed_with_raw(tmp_path, "old_job", "x")
    wing = Path(tmp_path / ".vedix" / "palace" / "vedix_kg__job__old_job")
    # Backdate mtime to 60 days ago
    old_ts = time.time() - 60 * 86400
    import os as _os
    _os.utime(wing, (old_ts, old_ts))
    removed = gc_command(older_than_days=30)
    assert "old_job" in removed
    assert not wing.exists()
