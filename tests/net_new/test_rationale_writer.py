"""Tests for §5.4 rationale-writer."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from plugins.vedix.mcp.lib.orchestrator.rationale_writer import write_rationale


@pytest.mark.asyncio
async def test_write_rationale(tmp_path):
    artifact_path = tmp_path / "hypothesis.md"
    artifact_path.write_text(
        "Hypothesis: temperature affects yield", encoding="utf-8"
    )
    fake_response = type(
        "R", (), {"content": "## Why this exists\n- the experimenter chose this..."}
    )()
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.dispatch.dispatch_agent",
        new=AsyncMock(return_value=fake_response),
    ):
        rationale = await write_rationale(
            artifact_path=artifact_path,
            artifact_kind="hypothesis",
            producing_agent="hypothesizer",
            decisions=[{"option": "exploratory", "alternative": "confirmatory"}],
        )
    assert rationale.exists()
    assert "Why this exists" in rationale.read_text(encoding="utf-8")
