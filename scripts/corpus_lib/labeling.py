"""Stage 7 — rule-based positive labeling.

A paragraph is labelled positive (in-register) iff:
  • Its section is one of the substantive IMRaD-style buckets we keep:
    Introduction, Methods, Results, Discussion, Conclusion, Body.
  • Its word count is in [40, 400] — short blurbs are mostly captions
    and very long blocks are usually a bad split.

References, Acknowledgements, Author Contributions, etc. are dropped.
"""
from __future__ import annotations

KEEP_SECTIONS: set[str] = {
    "Introduction",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "Body",
}


def label_positives(paragraphs: list[dict]) -> list[dict]:
    """Return paragraphs marked ``label=1`` with ``label_source="rule"``."""
    out: list[dict] = []
    for p in paragraphs:
        section = p.get("section")
        n_words = int(p.get("n_words", 0))
        if section in KEEP_SECTIONS and 40 <= n_words <= 400:
            out.append({**p, "label": 1, "label_source": "rule"})
    return out
