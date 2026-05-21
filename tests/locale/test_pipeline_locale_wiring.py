"""Integration tests: locale router → pipeline & anti-LLMish lint (B6 Task 5).

The pipeline exposes ``self.latex_engine`` derived from the language flag
(via :func:`get_locale`). ``lint_paragraph(text, language=...)`` consumes
the per-locale ``register_lints`` blacklist instead of the English-only
default tiered lint.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from plugins.vedix.mcp.lib.orchestrator.anti_llm_lint import lint_paragraph
from plugins.vedix.mcp.lib.orchestrator.pipeline import Pipeline


def _make_pipeline(language: str) -> Pipeline:
    """Construct a Pipeline with mocked dispatcher/evaluator + given lang."""
    return Pipeline(
        dispatcher=MagicMock(),
        evaluator=MagicMock(),
        language=language,
    )


def test_pipeline_picks_xelatex_for_chinese(tmp_path):
    p = _make_pipeline("zh")
    assert p.latex_engine == "xelatex"


def test_pipeline_picks_xelatex_for_japanese(tmp_path):
    p = _make_pipeline("ja")
    assert p.latex_engine == "xelatex"


def test_pipeline_picks_pdflatex_for_russian(tmp_path):
    p = _make_pipeline("ru")
    assert p.latex_engine == "pdflatex"


def test_pipeline_picks_pdflatex_for_english(tmp_path):
    p = _make_pipeline("en")
    assert p.latex_engine == "pdflatex"


def test_pipeline_picks_pdflatex_for_german(tmp_path):
    p = _make_pipeline("de")
    assert p.latex_engine == "pdflatex"


def test_pipeline_stores_locale_object(tmp_path):
    p = _make_pipeline("fr")
    assert p.locale.code == "fr"
    assert p.locale.babel_lang == "french"


def test_pipeline_default_language_is_english(tmp_path):
    """No language flag → defaults to English / pdflatex."""
    p = Pipeline(dispatcher=MagicMock(), evaluator=MagicMock())
    assert p.language == "en"
    assert p.latex_engine == "pdflatex"


# --- anti_llm_lint.lint_paragraph ------------------------------------------


def test_anti_llmish_lint_returns_language_key():
    result = lint_paragraph("plain text.", language="en")
    assert result["language"] == "en"
    assert "violations" in result


def test_anti_llmish_lint_uses_russian_blacklist():
    """Spec test from plan: «Кроме того,» triggers RU paragraph-start lint."""
    result = lint_paragraph("Кроме того, это работа.", language="ru")
    assert result["violations"]
    assert result["language"] == "ru"
    types = {v["type"] for v in result["violations"]}
    assert "paragraph_start" in types


def test_anti_llmish_lint_uses_english_blacklist():
    """«Furthermore,…» triggers EN paragraph-start lint."""
    result = lint_paragraph("Furthermore, the model is better.", language="en")
    assert result["violations"]
    types = {v["type"] for v in result["violations"]}
    assert "paragraph_start" in types


def test_anti_llmish_lint_flags_blacklist_word_en():
    """EN: 'delve' should be flagged (in blacklist_words)."""
    result = lint_paragraph(
        "We delve into the optimization landscape.", language="en"
    )
    types = {v["type"] for v in result["violations"]}
    assert "blacklist_word" in types


def test_anti_llmish_lint_clean_paragraph_passes():
    """A neutral sentence in a language with no triggers → no violations."""
    result = lint_paragraph("The model converged in five iterations.",
                            language="en")
    # Paragraph-start hits are anchored to startswith; "The" is not
    # blacklisted. Should be clean.
    assert result["violations"] == []
    assert result["language"] == "en"


def test_anti_llmish_lint_flags_em_dash_overuse_ru():
    """RU em-dash budget is 4/1000 words. 10 dashes in a 10-word sentence
    blows past the cap and triggers em_dash_overuse."""
    text = "Это — тест — с — большим — числом — тире — и — точкой — здесь — конец."
    result = lint_paragraph(text, language="ru")
    types = {v["type"] for v in result["violations"]}
    assert "em_dash_overuse" in types


def test_anti_llmish_lint_unknown_language_raises():
    """Unsupported codes propagate KeyError from the router."""
    import pytest

    with pytest.raises(KeyError):
        lint_paragraph("Some text.", language="ko")
