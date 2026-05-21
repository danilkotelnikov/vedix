"""Japanese locale stub (Task 1). Full config lands in Task 4."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="ja",
    name="Japanese",
    citation_style="jis-x-0202-japanese",
    latex_preamble="",
    bibtex_style="junsrt",
    latex_engine="xelatex",
    babel_lang="japanese",
    register_lints={},
)
