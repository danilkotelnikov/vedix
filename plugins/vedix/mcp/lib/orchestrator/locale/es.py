"""Spanish locale stub (Task 1). Full config lands in Task 4."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="es",
    name="Spanish",
    citation_style="biblatex-iso-690-2",
    latex_preamble="",
    bibtex_style="iso690-numeric-en",
    latex_engine="pdflatex",
    babel_lang="spanish",
    register_lints={},
)
