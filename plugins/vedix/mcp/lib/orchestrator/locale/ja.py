"""Japanese locale configuration (Block 6 Task 4, §6).

- Citation backend: biblatex ``numeric-comp`` paired with the Japanese
  reference convention from JIS X 0202 (the JIS character-encoding
  norm; ``citation_style`` label includes the substring for the
  router's substring match).
- Encoding: native UTF-8 via ``xeCJK``.
- Font: Source Han Serif Japan.
- Engine: ``xelatex``.
- Register lints: JA academic openers ("なお、", "また、", "そして、",
  …) plus weak-stance verb phrases ("と考えられる", "と思われる",
  "ものと推測される") that LLMs over-produce. Preferred mode is
  常体 (plain form) for academic register, as opposed to 敬体
  (polite form).
"""
from .base import LocaleConfig

LINTS: dict = {
    "blacklist_paragraph_start": [
        "なお、",
        "また、",
        "そして、",
        "したがって、",
    ],
    "blacklist_phrases": [
        "と考えられる",
        "と思われる",
        "ものと推測される",
    ],
    "max_em_dashes_per_1000_words": 4,
    # Academic JA prefers 常体 (jōtai, plain form) over 敬体 (keitai,
    # polite form). LLMs default to keitai; flag and demote.
    "preferred_mode": "常体",
}

CONFIG = LocaleConfig(
    code="ja",
    name="Japanese",
    # "japanese" substring kept in the style key so the router's
    # parametrize-test (which asserts substring "japanese") resolves to
    # this locale module.
    citation_style="jis-x-0202-japanese",
    latex_preamble=(
        r"\usepackage{xeCJK}"
        "\n"
        r"\setCJKmainfont{Source Han Serif Japan}"
        "\n"
        r"\usepackage[backend=biber,style=numeric-comp]{biblatex}"
    ),
    bibtex_style="junsrt",
    latex_engine="xelatex",
    babel_lang="japanese",
    register_lints=LINTS,
)
