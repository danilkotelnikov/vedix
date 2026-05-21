"""French locale configuration (Block 6 Task 4, §6).

- Citation backend: biblatex ``numeric-comp`` per NF Z44-005 (the French
  AFNOR norm for bibliographic references).
- Encoding: T1 fontenc + UTF-8 (accented vowels, ç).
- Font: Latin Modern via ``lmodern``.
- Engine: ``pdflatex``.
- Register lints: French academic openers ("Il est à noter que", "Il
  convient de souligner", …) and over-used evaluative adjectives
  ("primordial", "essentiel", "fondamental").
"""
from .base import LocaleConfig

LINTS: dict = {
    "blacklist_paragraph_start": [
        "Il est à noter que",
        "Il convient de souligner",
        "En effet",
        "Par ailleurs",
        "De plus",
        "À cet égard",
    ],
    "blacklist_words": [
        "primordial",
        "essentiel",
        "fondamental",
    ],
    "max_em_dashes_per_1000_words": 3,
}

CONFIG = LocaleConfig(
    code="fr",
    name="French",
    citation_style="biblatex-nfz44-005",
    latex_preamble=(
        r"\usepackage[utf8]{inputenc}"
        "\n"
        r"\usepackage[T1]{fontenc}"
        "\n"
        r"\usepackage{lmodern}"
        "\n"
        r"\usepackage[french]{babel}"
        "\n"
        r"\usepackage[backend=biber,style=numeric-comp]{biblatex}"
    ),
    bibtex_style="francais",
    latex_engine="pdflatex",
    babel_lang="french",
    register_lints=LINTS,
)
