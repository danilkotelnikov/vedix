"""German locale configuration (Block 6 Task 4, §6).

- Citation backend: biblatex ``numeric-comp`` keyed to ``de_DE`` sort
  locale, conforming to DIN 1505-2 (German academic citation rules).
- Encoding: T1 fontenc + UTF-8 (umlauts, ß).
- Font: Latin Modern via ``lmodern``.
- Engine: ``pdflatex``.
- Register lints: stock German academic openers ("Hierbei", "Hingegen",
  "Darüber hinaus", …) and over-used intensifiers ("umfassend",
  "weitreichend", "tiefgreifend"). Also caps nominalization rate
  (German over-nominalizes; cap at 0.30 of content words).
"""
from .base import LocaleConfig

LINTS: dict = {
    "blacklist_paragraph_start": [
        "Hierbei",
        "Hingegen",
        "Darüber hinaus",
        "Folglich",
        "Es ist wichtig zu betonen",
        "Bekanntlich",
    ],
    "blacklist_words": [
        "umfassend",
        "weitreichend",
        "tiefgreifend",
    ],
    "max_em_dashes_per_1000_words": 2,
    # German prose drifts towards Substantivstil (-ung / -heit / -keit
    # endings). Cap nominalization ratio at 0.30 to keep verbs primary.
    "max_nominalization_rate": 0.30,
}

CONFIG = LocaleConfig(
    code="de",
    name="German",
    citation_style="biblatex-din-1505-2",
    latex_preamble=(
        r"\usepackage[utf8]{inputenc}"
        "\n"
        r"\usepackage[T1]{fontenc}"
        "\n"
        r"\usepackage{lmodern}"
        "\n"
        r"\usepackage[ngerman]{babel}"
        "\n"
        r"\usepackage[backend=biber,style=numeric-comp,sortlocale=de_DE]{biblatex}"
    ),
    bibtex_style="din1505-numeric",
    latex_engine="pdflatex",
    babel_lang="ngerman",
    register_lints=LINTS,
)
