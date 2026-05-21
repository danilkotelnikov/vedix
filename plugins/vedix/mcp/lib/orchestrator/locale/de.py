"""German locale stub (Task 1). Full config lands in Task 4."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="de",
    name="German",
    citation_style="biblatex-din-1505-2",
    latex_preamble="",
    bibtex_style="din1505-numeric",
    latex_engine="pdflatex",
    babel_lang="ngerman",
    register_lints={},
)
