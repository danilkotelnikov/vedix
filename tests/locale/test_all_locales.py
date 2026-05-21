"""Tests for all 7 first-class locales (B6 Task 4, §6).

Each locale exports a valid :class:`LocaleConfig` with the right engine,
non-empty preamble + lints, and a babel/polyglossia language name. CJK
locales route to xelatex; Latin/Cyrillic to pdflatex.
"""
from __future__ import annotations

import pytest

from plugins.vedix.mcp.lib.orchestrator.locale.router import (
    get_locale,
    list_locales,
)


ALL_CODES = ("en", "ru", "es", "de", "fr", "zh", "ja")


@pytest.mark.parametrize("code", ALL_CODES)
def test_locale_has_required_fields(code):
    loc = get_locale(code)
    assert loc.code == code
    assert loc.name
    assert loc.citation_style
    assert loc.latex_preamble
    assert loc.latex_engine in ("pdflatex", "xelatex")
    assert loc.babel_lang
    assert loc.register_lints


@pytest.mark.parametrize("code", ALL_CODES)
def test_locale_has_blacklist_paragraph_start(code):
    loc = get_locale(code)
    starters = loc.register_lints.get("blacklist_paragraph_start", [])
    assert isinstance(starters, list)
    assert len(starters) >= 4, (
        f"{code}: expected ≥4 paragraph-start starters; got {len(starters)}"
    )


@pytest.mark.parametrize("code", ALL_CODES)
def test_locale_has_em_dash_budget(code):
    loc = get_locale(code)
    budget = loc.register_lints.get("max_em_dashes_per_1000_words")
    assert budget is not None
    assert isinstance(budget, int)
    assert 1 <= budget <= 10


def test_cjk_languages_use_xelatex():
    for code in ("zh", "ja"):
        assert get_locale(code).latex_engine == "xelatex", (
            f"{code} should use xelatex"
        )


def test_latin_cyrillic_use_pdflatex():
    for code in ("en", "ru", "es", "de", "fr"):
        assert get_locale(code).latex_engine == "pdflatex", (
            f"{code} should use pdflatex"
        )


def test_all_locales_listed():
    assert set(list_locales()) == set(ALL_CODES)


def test_ru_em_dash_budget_is_4():
    """Spec: RU register tolerates 4 em-dashes / 1000 words."""
    assert get_locale("ru").register_lints["max_em_dashes_per_1000_words"] == 4


def test_en_em_dash_budget_is_2():
    """Spec: EN register baseline is 2 em-dashes / 1000 words (human)."""
    assert get_locale("en").register_lints["max_em_dashes_per_1000_words"] == 2


def test_ja_preferred_mode_is_plain():
    """Spec: JA academic register prefers 常体 (plain form)."""
    assert get_locale("ja").register_lints["preferred_mode"] == "常体"


def test_de_has_nominalization_cap():
    """Spec: German caps nominalization rate to combat Substantivstil."""
    assert "max_nominalization_rate" in get_locale("de").register_lints


def test_zh_uses_ctex():
    """Spec: ZH preamble loads the ctex package for CJK."""
    assert "ctex" in get_locale("zh").latex_preamble


def test_ru_uses_t2a_fontenc():
    """Spec: RU preamble loads T2A fontenc for Cyrillic glyphs."""
    assert "T2A" in get_locale("ru").latex_preamble


def test_ru_citation_style_is_gost():
    """Spec: RU citation backend is gost-numeric (ГОСТ 7.0.5-2008)."""
    assert "gost" in get_locale("ru").citation_style.lower()


def test_zh_citation_style_is_gbt7714():
    """Spec: ZH citation backend is GB/T 7714-2015."""
    assert "gbt7714" in get_locale("zh").citation_style.lower()
