import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from plugins.vedix.mcp.lib.orchestrator.pipeline import Pipeline


@pytest.mark.asyncio
async def test_pipeline_runs_graph_builder_between_L_and_H(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    p = Pipeline(workspace=tmp_path, language="en")
    phases = p.list_phase_order()
    assert phases.index("literature_search") < phases.index("graph_builder") < phases.index("hypothesizer")


@pytest.mark.asyncio
async def test_manuscript_writer_uses_paragraph_planner(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    p = Pipeline(workspace=tmp_path, language="en")
    hooks = p.list_hooks()
    assert "compute_allowed_set" in hooks
    assert "verify_sentence" in hooks


def test_references_reads_from_kg(tmp_path, monkeypatch):
    from plugins.vedix.mcp.lib.orchestrator.references import bibtex_from_kg
    from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
    from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
        KGFragment, KGNodes, Author, RawPointer,
    )
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    store = KGStore(tier=Tier.JOB, scope_id="refs1")
    store.write_paper(KGFragment(
        paper_id="smith2024", doi="10.1/x", title="The Title", year=2024,
        authors=[Author(id="author:s", name="J Smith")],
        venue="JACS", language="en", license="CC-BY",
        raw_pointer=RawPointer(text="raw/x.txt", byte_len=10),
        nodes=KGNodes(),
        edges=[],
    ))
    bib = bibtex_from_kg(store=store)
    assert "@article{smith2024" in bib
    assert "doi = {10.1/x}" in bib
    assert "title = {The Title}" in bib


def test_reviewer_kg_scope_id_naming():
    from plugins.vedix.mcp.lib.orchestrator.reviewer_ledger import reviewer_kg_scope_id
    assert reviewer_kg_scope_id(reviewer_id="1", job_id="abc123") == "1__abc123"
