"""Russian locale stub (Task 1). Full config lands in Task 3."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="ru",
    name="Russian",
    citation_style="gost-numeric",
    latex_preamble="",
    bibtex_style="gost71s",
    latex_engine="pdflatex",
    babel_lang="russian",
    register_lints={},
)
