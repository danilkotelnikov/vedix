"""French locale stub (Task 1). Full config lands in Task 4."""
from .base import LocaleConfig

CONFIG = LocaleConfig(
    code="fr",
    name="French",
    citation_style="biblatex-nfz44-005",
    latex_preamble="",
    bibtex_style="francais",
    latex_engine="pdflatex",
    babel_lang="french",
    register_lints={},
)
