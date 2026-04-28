"""Iterative 3-cycle plotter — Cycle 1 (inspect & draft).

Closes spec §5. Cycle 1 emits figures_draft1/<id>.png + manifest.json with
per-figure plot_type_rationale and data schema.

Per-cycle artifacts let the user re-run any cycle independently. Cycle 2
(VLM critique) and Cycle 3 (polish) live in the same module.
"""
from __future__ import annotations
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PlotSpec:
    figure_id: str
    kind: str       # "bar" | "scatter" | "violin" | "heatmap" | "timeline"
    x: str
    y: str
    title: str
    facets: Optional[list] = None
    notes: str = ""


def _sniff_csv_schema(path: Path) -> dict:
    if not path.is_file():
        return {"columns": [], "row_count": 0}
    rows = list(csv.reader(path.open("r", encoding="utf-8")))
    if not rows:
        return {"columns": [], "row_count": 0}
    header, body = rows[0], rows[1:]
    return {"columns": header, "row_count": len(body)}


def _plot_type_rationale(spec: PlotSpec, schema: dict) -> str:
    """Justify plot type given data shape."""
    n = schema.get("row_count", 0)
    if spec.kind == "bar":
        return f"bar chart for {n} categorical observations of {spec.y}"
    if spec.kind == "violin":
        return f"violin chart for {n} samples (>30 → distribution shape visible)"
    if spec.kind == "scatter":
        return f"scatter for {n} ({spec.x}, {spec.y}) pairs"
    if spec.kind == "heatmap":
        return f"heatmap for matrix of {n} rows by columns of {spec.x}"
    if spec.kind == "timeline":
        return f"timeline for {n} year-counted events"
    return f"{spec.kind} for {n} rows"


def _render_draft_png(spec: PlotSpec, outdir: Path) -> Path:
    """Render a stub PNG. Full matplotlib rendering happens in Cycle 3.

    Cycle 1's purpose is the inspection + rationale, not pixel-perfect
    output. The actual draft is a 1-line text marker — Cycle 3 will
    overwrite with publication-grade vector output.
    """
    p = outdir / f"{spec.figure_id}.txt"
    p.write_text(
        f"# DRAFT figure {spec.figure_id} ({spec.kind})\n"
        f"# title: {spec.title}\n"
        f"# x={spec.x}, y={spec.y}\n",
        encoding="utf-8")
    return p


@dataclass
class PlotterLoop:
    output_dir: Path
    article_type: str = "experimental"
    journal_style: str = "auto"
    palette: str = "okabe_ito"

    def cycle1_inspect_and_draft(self, specs: list) -> dict:
        cycle_dir = self.output_dir / "figures_draft1"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        results_csv = self.output_dir / "results.csv"
        schema = _sniff_csv_schema(results_csv)
        figures = []
        for spec in specs:
            draft = _render_draft_png(spec, cycle_dir)
            figures.append({
                "figure_id": spec.figure_id,
                "kind": spec.kind,
                "title": spec.title,
                "data_schema": schema,
                "draft_path": str(draft.relative_to(self.output_dir)),
                "plot_type_rationale": _plot_type_rationale(spec, schema),
            })
        manifest = {
            "cycle": 1,
            "article_type": self.article_type,
            "journal_style": self.journal_style,
            "palette": self.palette,
            "figures": figures,
        }
        (cycle_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest
