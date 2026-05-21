"""Simplified Chinese locale configuration (Block 6 Task 4, §6).

- Citation backend: ``gbt7714`` package implementing GB/T 7714-2015,
  the Chinese national standard for academic references (numerical
  flavour).
- Encoding: native UTF-8 via the ``ctex`` + ``fontspec`` stack.
- Font: Source Han Serif SC (CJK serif; ships in Adobe's open-source
  pan-CJK family).
- Engine: ``xelatex`` (required for ``fontspec`` and CJK script).
- Register lints: ZH academic stock openers ("综上所述", "总而言之",
  …) plus filler phrases ("不仅...而且", "在...的过程中"). Em-dash
  budget bumped to 5/1000 — CJK convention uses 破折号 more
  liberally than EN.
"""
from .base import LocaleConfig

LINTS: dict = {
    "blacklist_paragraph_start": [
        "综上所述",
        "总而言之",
        "由此可见",
        "值得注意的是",
    ],
    "blacklist_phrases": [
        "不仅...而且",
        "在...的过程中",
        "通过...的方式",
    ],
    "max_em_dashes_per_1000_words": 5,
}

CONFIG = LocaleConfig(
    code="zh",
    name="Chinese (Simplified)",
    citation_style="gbt7714-2015",
    latex_preamble=(
        r"\usepackage{ctex}"
        "\n"
        r"\usepackage{fontspec}"
        "\n"
        r"\setCJKmainfont{Source Han Serif SC}"
        "\n"
        r"\usepackage{gbt7714}"
        "\n"
        r"\bibliographystyle{gbt7714-numerical}"
    ),
    bibtex_style="gbt7714-numerical",
    latex_engine="xelatex",
    babel_lang="chinese-simplified",
    register_lints=LINTS,
)
