import pytest
from pathlib import Path
from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    KGFragment, KGNodes, Claim, Author, RawPointer, Provenance, Edge,
)


def _frag(pid="smith2024", claim_id="smith2024.c1"):
    return KGFragment(
        paper_id=pid, doi=f"10.1/{pid}", title="t", year=2024,
        authors=[Author(id="author:x", name="X")],
        venue="J", language="en", license="CC-BY",
        raw_pointer=RawPointer(text=f"raw/{pid}.txt", byte_len=100),
        nodes=KGNodes(claims=[
            Claim(id=claim_id, type="empirical", paraphrase="p",
                  verbatim_quote="abc", quote_byte_range=[0, 3],
                  page=1, section="Results", confidence=0.9, hedge=False,
                  provenance=Provenance(extractor_model="x", extractor_ts=0)),
        ]),
        edges=[],
    )


def test_write_and_read_paper_job_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.JOB, scope_id="job123")
    frag = _frag()
    store.write_paper(frag)
    loaded = store.read_paper("smith2024")
    assert loaded.paper_id == "smith2024"
    assert loaded.nodes.claims[0].verbatim_quote == "abc"


def test_write_and_read_paper_project_tier(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.PROJECT, scope_id="proj_abc")
    store.write_paper(_frag())
    assert store.read_paper("smith2024").paper_id == "smith2024"


def test_tiers_are_isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    job = KGStore(tier=Tier.JOB, scope_id="j1")
    proj = KGStore(tier=Tier.PROJECT, scope_id="p1")
    job.write_paper(_frag(pid="paper_in_job", claim_id="paper_in_job.c1"))
    assert proj.read_paper("paper_in_job") is None
    assert job.read_paper("paper_in_job") is not None


def test_write_edge_and_traverse(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.JOB, scope_id="j1")
    store.write_paper(_frag(pid="a", claim_id="a.c1"))
    store.write_paper(_frag(pid="b", claim_id="b.c1"))
    store.write_edge(Edge(**{"from": "a.c1", "to": "b.c1", "kind": "extends", "confidence": 0.9}))
    edges_out = store.edges_from("a.c1")
    assert any(e.to == "b.c1" and e.kind == "extends" for e in edges_out)
    edges_in = store.edges_to("b.c1")
    assert any(e.from_ == "a.c1" for e in edges_in)


def test_list_papers_returns_all_written(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.JOB, scope_id="j1")
    store.write_paper(_frag(pid="a", claim_id="a.c1"))
    store.write_paper(_frag(pid="b", claim_id="b.c1"))
    ids = sorted(store.list_paper_ids())
    assert ids == ["a", "b"]


def test_kg_revision_id_changes_after_write(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.JOB, scope_id="j1")
    rev0 = store.kg_revision_id()
    store.write_paper(_frag(pid="a", claim_id="a.c1"))
    rev1 = store.kg_revision_id()
    assert rev0 != rev1
