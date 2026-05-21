"""§4.6 Pre-registration replay.

The user (or upstream phase) writes a small ``prereg.md`` file naming the
hypothesis, primary metric, and expected direction. ``gate_experiment``
refuses to run if the file is missing or malformed. ``audit_results``
compares the recorded outcome against the prereg and raises
``PreregViolation`` on metric-swap or direction-reversal — the classic
HARKing / post-hoc-redefinition smells.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class PreregViolation(Exception):
    """Raised on missing prereg, malformed prereg, or post-hoc redefinition."""


def write_prereg(prereg: dict, dest: Path) -> Path:
    """Write the prereg as markdown the human can read + a yaml block we can parse."""
    md = "# Pre-registration\n\n"
    md += f"**Hypothesis:** {prereg.get('hypothesis', '')}\n\n"
    md += f"**Primary metric:** {prereg.get('primary_metric', '')}\n\n"
    md += f"**Expected direction:** {prereg.get('expected_direction', '')}\n\n"
    md += f"**Tolerance:** {prereg.get('tolerance', '')}\n\n"
    md += "```yaml\n" + json.dumps(prereg, indent=2) + "\n```\n"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(md, encoding="utf-8")
    return dest


def _parse_prereg(prereg_path: Path) -> dict[str, Any]:
    text = prereg_path.read_text(encoding="utf-8")
    yaml_block = re.search(r"```yaml\n(.+?)\n```", text, re.DOTALL)
    if not yaml_block:
        raise PreregViolation(
            f"prereg at {prereg_path} has no machine-readable yaml block",
        )
    return json.loads(yaml_block.group(1))


def gate_experiment(*, prereg_path: Path) -> None:
    """Hard-gate: must exist + parse + have required fields."""
    if not prereg_path.exists():
        raise PreregViolation(
            f"prereg required but {prereg_path} does not exist; "
            "create one before running the experiment",
        )
    p = _parse_prereg(prereg_path)
    required = {"hypothesis", "primary_metric", "expected_direction"}
    missing = required - set(p.keys())
    if missing:
        raise PreregViolation(f"prereg missing keys: {missing}")


def audit_results(*, prereg_path: Path, actual: dict) -> dict[str, Any]:
    """Compare actual outcome to prereg; raise on metric-swap or direction-reversal."""
    p = _parse_prereg(prereg_path)
    violations: list[str] = []
    if actual.get("primary_metric") != p.get("primary_metric"):
        violations.append(
            f"primary metric swapped: "
            f"prereg={p['primary_metric']!r}, actual={actual.get('primary_metric')!r}",
        )
    actual_dir = actual.get("direction")
    expected_dir = p.get("expected_direction")
    if actual_dir and expected_dir and actual_dir != expected_dir:
        violations.append(
            f"direction reversed: prereg={expected_dir!r}, actual={actual_dir!r}",
        )
    if violations:
        raise PreregViolation(" | ".join(violations))
    return {"prereg": p, "actual": actual, "violations": [], "status": "ok"}
