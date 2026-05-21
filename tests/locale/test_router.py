"""Tests for the locale router and LocaleConfig protocol (B6 Task 1)."""
from __future__ import annotations

import pytest

from plugins.vedix.mcp.lib.orchestrator.locale.router import (
    get_locale,
    list_locales,
)


@pytest.mark.parametrize(
    "code,citation_substr,engine",
    [
        ("en", "biblatex", "pdflatex"),
        ("ru", "gost", "pdflatex"),
        ("zh", "gbt7714", "xelatex"),
        ("ja", "japanese", "xelatex"),
        ("es", "iso-690", "pdflatex"),
        ("de", "din", "pdflatex"),
        ("fr", "nfz44", "pdflatex"),
    ],
)
def test_router_returns_correct_locale(code, citation_substr, engine):
    loc = get_locale(code)
    assert loc.code == code
    assert citation_substr.lower() in loc.citation_style.lower()
    assert loc.latex_engine == engine


def test_router_raises_unknown():
    with pytest.raises(KeyError):
        get_locale("ko")


def test_list_locales_returns_all_seven():
    assert set(list_locales()) == {"en", "ru", "es", "de", "fr", "zh", "ja"}
