"""English locale stub (Task 1). Full config lands in Task 2."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="en",
    name="English",
    citation_style="biblatex-numeric-comp",
    latex_preamble="",
    bibtex_style="ieeetr",
    latex_engine="pdflatex",
    babel_lang="english",
    register_lints={},
)
