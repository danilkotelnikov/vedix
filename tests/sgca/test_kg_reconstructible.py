import pytest
from pathlib import Path
from plugins.vedix.mcp.lib.orchestrator.sgca.cli import verify_command
from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    KGFragment, KGNodes, Claim, Author, RawPointer, Provenance,
)


def test_every_claim_quote_appears_in_raw(tmp_path, monkeypatch):
    """SGCA §8.5 — for every Claim, raw[byte_range] must equal verbatim_quote."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    raw_dir = tmp_path / ".vedix" / "jobs" / "recon" / "raw"
    raw_dir.mkdir(parents=True)
    raw_text = "The cat sat on the mat. The dog barked at the moon."
    raw_path = raw_dir / "p.txt"
    raw_path.write_text(raw_text, encoding="utf-8")

    store = KGStore(tier=Tier.JOB, scope_id="recon")
    store.write_paper(KGFragment(
        paper_id="p", doi="10/p", title="t", year=2024,
        authors=[Author(id="author:x", name="x")], language="en", license="CC-BY",
        raw_pointer=RawPointer(text=str(raw_path), byte_len=len(raw_text)),
        nodes=KGNodes(claims=[
            Claim(id="p.c1", type="empirical", paraphrase="cat sat",
                  verbatim_quote="The cat sat on the mat.",
                  quote_byte_range=[0, 23],
                  page=1, section="Results", confidence=0.9, hedge=False,
                  provenance=Provenance(extractor_model="x", extractor_ts=0)),
        ]),
        edges=[],
    ))
    report = verify_command(tier=Tier.JOB, scope_id="recon")
    assert report["ok"] is True
