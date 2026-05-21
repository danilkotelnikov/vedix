"""Spanish locale configuration (Block 6 Task 4, §6).

- Citation backend: biblatex ``iso-numeric`` (ISO-690-2, the Spanish
  national + Latin-American academic standard).
- Encoding: T1 fontenc + UTF-8 input (covers ñ, accented vowels).
- Font: Latin Modern via ``lmodern``.
- Engine: ``pdflatex``.
- Register lints: paragraph-starter clichés ("Es importante destacar",
  "Cabe señalar", …) and over-used evaluative adjectives ("crucial",
  "imprescindible") that AI scrubbers consistently flag.
"""
from .base import LocaleConfig

LINTS: dict = {
    "blacklist_paragraph_start": [
        "Es importante destacar",
        "Cabe señalar",
        "Es decir",
        "En este sentido",
        "Por lo tanto",
        "Asimismo",
    ],
    "blacklist_words": [
        "fundamental",
        "crucial",
        "imprescindible",
    ],
    "max_em_dashes_per_1000_words": 3,
}

CONFIG = LocaleConfig(
    code="es",
    name="Spanish",
    citation_style="biblatex-iso-690-2",
    latex_preamble=(
        r"\usepackage[utf8]{inputenc}"
        "\n"
        r"\usepackage[T1]{fontenc}"
        "\n"
        r"\usepackage{lmodern}"
        "\n"
        r"\usepackage[spanish]{babel}"
        "\n"
        r"\usepackage[backend=biber,style=iso-numeric]{biblatex}"
    ),
    bibtex_style="iso690-numeric-en",
    latex_engine="pdflatex",
    babel_lang="spanish",
    register_lints=LINTS,
)
