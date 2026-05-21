"""Simplified Chinese locale stub (Task 1). Full config lands in Task 4."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="zh",
    name="Chinese (Simplified)",
    citation_style="gbt7714-2015",
    latex_preamble="",
    bibtex_style="gbt7714-numerical",
    latex_engine="xelatex",
    babel_lang="chinese-simplified",
    register_lints={},
)
