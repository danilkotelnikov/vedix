"""LocaleConfig dataclass — shared protocol for all 7 first-class locales.

See ``docs/specs/2026-04-30-v3-major-release-spec.md`` §6 and
``docs/superpowers/plans/2026-05-20-block06-languages.md`` Task 1.

Each language module (``en.py``, ``ru.py``, …) exports a ``CONFIG`` of
this type. The pipeline + anti-LLMish lint consume these via
:mod:`.router`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LocaleConfig:
    """Single source of truth for one language's typesetting + lint policy.

    Attributes:
        code: ISO 639-1 (``en``, ``ru``, ``zh``, ``ja``, …).
        name: Human-readable name (``"English"``, ``"Russian"``, …).
        citation_style: Biblatex style identifier (e.g. ``"gost-numeric"``,
            ``"biblatex-numeric-comp"``, ``"gbt7714-2015"``).
        latex_preamble: ``\\usepackage{…}`` lines to splice into manuscript
            preamble; varies by script (Latin / Cyrillic / CJK).
        bibtex_style: Legacy BibTeX style (used only if biblatex is
            unavailable in the target template).
        latex_engine: One of ``"pdflatex"`` (Latin/Cyrillic) or
            ``"xelatex"`` (CJK). Pipeline.latex_engine is derived from
            this.
        babel_lang: Name passed to ``\\usepackage[…]{babel}`` /
            ``\\setdefaultlanguage{…}`` for polyglossia.
        register_lints: Per-language anti-LLMish blacklist (paragraph
            starts, words, em-dash budget). Consumed by
            :func:`anti_llm_lint.lint_paragraph`.
        bib_preserve_orthography: Keep original script (Cyrillic /
            CJK) in references rather than transliterating.
    """

    code: str
    name: str
    citation_style: str
    latex_preamble: str
    bibtex_style: str
    latex_engine: str
    babel_lang: str
    register_lints: dict[str, Any] = field(default_factory=dict)
    bib_preserve_orthography: bool = True
