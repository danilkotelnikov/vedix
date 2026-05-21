"""Tests for §4.6 pre-registration replay."""
from __future__ import annotations

import pytest

from plugins.vedix.mcp.lib.orchestrator.prereg_replay import (
    PreregViolation, audit_results, gate_experiment, write_prereg,
)


def test_write_and_gate(tmp_path):
    prereg = {
        "hypothesis": "X improves Y",
        "primary_metric": "accuracy",
        "expected_direction": "increase",
        "tolerance": 0.05,
    }
    p = write_prereg(prereg, dest=tmp_path / "prereg.md")
    assert p.exists()
    gate_experiment(prereg_path=p)


def test_audit_detects_metric_swap(tmp_path):
    prereg = {
        "hypothesis": "X improves Y",
        "primary_metric": "accuracy",
        "expected_direction": "increase",
    }
    p = write_prereg(prereg, dest=tmp_path / "prereg.md")
    actual = {
        "primary_metric": "loss", "value": 0.4, "direction": "decrease",
    }
    with pytest.raises(PreregViolation):
        audit_results(prereg_path=p, actual=actual)


def test_audit_passes_when_consistent(tmp_path):
    prereg = {
        "hypothesis": "X improves Y",
        "primary_metric": "accuracy",
        "expected_direction": "increase",
    }
    p = write_prereg(prereg, dest=tmp_path / "prereg.md")
    actual = {
        "primary_metric": "accuracy", "value": 0.85, "direction": "increase",
    }
    audit_results(prereg_path=p, actual=actual)
