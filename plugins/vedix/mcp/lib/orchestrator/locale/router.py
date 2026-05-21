"""Central router that selects a :class:`base.LocaleConfig` by ISO 639-1 code.

Block 6 (§6) — covers the 7 first-class languages: ``en``, ``ru``, ``es``,
``de``, ``fr``, ``zh``, ``ja``. The pipeline reads
``get_locale(language).latex_engine`` to dispatch between ``pdflatex``
(Latin / Cyrillic) and ``xelatex`` (CJK).
"""
from __future__ import annotations

from . import de, en, es, fr, ja, ru, zh
from .base import LocaleConfig

_LOCALES: dict[str, LocaleConfig] = {
    "en": en.CONFIG,
    "ru": ru.CONFIG,
    "es": es.CONFIG,
    "de": de.CONFIG,
    "fr": fr.CONFIG,
    "zh": zh.CONFIG,
    "ja": ja.CONFIG,
}


def get_locale(code: str) -> LocaleConfig:
    """Return the :class:`LocaleConfig` for ``code`` or raise ``KeyError``.

    >>> get_locale("en").latex_engine
    'pdflatex'
    >>> get_locale("zh").latex_engine
    'xelatex'
    """
    if code not in _LOCALES:
        raise KeyError(
            f"locale {code!r} not supported; available: {sorted(_LOCALES)}"
        )
    return _LOCALES[code]


def list_locales() -> list[str]:
    """Sorted list of all supported ISO 639-1 codes."""
    return sorted(_LOCALES)
