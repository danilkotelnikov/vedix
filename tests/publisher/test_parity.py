"""Block 7 Task 4 — LaTeX↔Word parity check tests.

`check_parity()` returns ``status="ok"`` when PDF + DOCX artifact counts
match within tolerance, ``status="drift"`` otherwise, with per-axis
divergences enumerated in the result. We mock the inspectors so the
test runs without a working LaTeX toolchain.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from plugins.vedix.mcp.lib.orchestrator.publisher_engine import (
    _count_artifacts_in_text,
    check_parity,
)


def _matched_data() -> dict:
    return {
        "sections": ["Intro", "Methods"],
        "n_equations": 5,
        "n_figures": 2,
        "n_tables": 1,
        "n_references": 12,
        "word_count": 5000,
        "n_citations": 12,
    }


def test_parity_passes_when_counts_match(tmp_path: Path):
    pdf_data = _matched_data()
    docx_data = {**_matched_data(), "word_count": 5050}  # within 2% tolerance
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=pdf_data,
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=docx_data,
    ):
        report = check_parity(pdf=tmp_path / "a.pdf", docx=tmp_path / "a.docx")
    assert report["status"] == "ok"
    assert report["divergences"] == []


def test_parity_flags_section_drift(tmp_path: Path):
    pdf_data = {**_matched_data(), "sections": ["Intro", "Methods", "Results"]}
    docx_data = {**_matched_data(), "word_count": 5050}
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=pdf_data,
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=docx_data,
    ):
        report = check_parity(pdf=tmp_path / "a.pdf", docx=tmp_path / "a.docx")
    assert report["status"] == "drift"
    assert any("section" in d["kind"] for d in report["divergences"])


def test_parity_flags_equation_count(tmp_path: Path):
    pdf_data = _matched_data()
    docx_data = {**_matched_data(), "n_equations": 4}
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=pdf_data,
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=docx_data,
    ):
        report = check_parity(pdf=tmp_path / "a.pdf", docx=tmp_path / "a.docx")
    assert report["status"] == "drift"
    kinds = {d["kind"] for d in report["divergences"]}
    assert "n_equations" in kinds


def test_parity_flags_word_count_outside_tolerance(tmp_path: Path):
    pdf_data = _matched_data()
    # 5000 vs 5500 = 10% drift, breaches the 2% default tolerance.
    docx_data = {**_matched_data(), "word_count": 5500}
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=pdf_data,
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=docx_data,
    ):
        report = check_parity(pdf=tmp_path / "a.pdf", docx=tmp_path / "a.docx")
    assert report["status"] == "drift"
    assert any(d["kind"] == "word_count" for d in report["divergences"])


def test_parity_respects_custom_tolerance(tmp_path: Path):
    pdf_data = _matched_data()
    docx_data = {**_matched_data(), "word_count": 5500}
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=pdf_data,
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=docx_data,
    ):
        report = check_parity(
            pdf=tmp_path / "a.pdf",
            docx=tmp_path / "a.docx",
            word_tolerance_pct=15.0,
        )
    assert report["status"] == "ok"


def test_parity_report_carries_raw_data(tmp_path: Path):
    with patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_pdf",
        return_value=_matched_data(),
    ), patch(
        "plugins.vedix.mcp.lib.orchestrator.publisher_engine._inspect_docx",
        return_value=_matched_data(),
    ):
        report = check_parity(pdf=tmp_path / "a.pdf", docx=tmp_path / "a.docx")
    assert report["pdf_data"]["n_references"] == 12
    assert report["docx_data"]["n_references"] == 12


def test_count_artifacts_in_text_basic():
    text = (
        "1. Introduction\n"
        "Some intro. See [1] and [2].\n"
        "Figure 1 shows the result.\n"
        "Table 1 lists parameters.\n"
        "\\begin{equation} a = b \\end{equation}\n"
        "\n"
        "[1] Smith J. 2024.\n"
        "[2] Doe J. 2023.\n"
    )
    counts = _count_artifacts_in_text(text)
    assert counts["n_equations"] >= 1
    assert counts["n_figures"] >= 1
    assert counts["n_tables"] >= 1
    assert counts["n_references"] >= 2
    assert counts["n_citations"] >= 2
    assert counts["word_count"] > 0
