"""Tests for the pipeline hook registry exposing the 7 rigor tracks."""
from __future__ import annotations

from plugins.vedix.mcp.lib.orchestrator.pipeline import Pipeline


def _make_pipeline():
    """Construct a Pipeline with the minimum set of no-op stubs."""
    return Pipeline(dispatcher=lambda **_: {}, evaluator=lambda _: {})


def test_rigor_tracks_registered():
    pipe = _make_pipeline()
    hooks = pipe.list_hooks()
    expected = {
        "failure_mode_check",
        "citation_graph_analysis",
        "counterfactual_probe",
        "adversarial_review",
        "semantic_revision_diff",
        "prereg_gate",
        "prereg_audit",
        "provenance_record",
        "disclosure_generate",
    }
    assert expected.issubset(hooks)
