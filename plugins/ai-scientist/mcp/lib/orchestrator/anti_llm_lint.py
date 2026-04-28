"""Anti-LLMish lint — empirically-grounded blacklist + style metrics.

Closes review-doc + spec §6.1. Sources: Liang et al. 2024 (PubMed 15M
abstracts), ICLR 2024 peer-review excess-vocabulary study.
"""
from __future__ import annotations
import re
from typing import Optional

# Tier 1 — measured ≥9× excess in post-ChatGPT corpora; block on first hit.
TIER1_BLACKLIST = [
    "delve", "delves", "delving", "delved",
    "underscore", "underscores", "underscoring", "underscored",
    "intricate", "intricacies", "intricately",
    "showcase", "showcases", "showcasing", "showcased",
    "meticulous", "meticulously",
    "commendable",
]

# Tier 2 — strong signal across editorial sources; warn on ≥2 in a section.
TIER2_BLACKLIST = [
    "robust", "landscape", "vibrant", "tapestry", "testament",
    "leverages", "leverage", "harness", "harnesses", "harnessing",
    "foster", "fosters", "fostering",
    "navigate", "navigates", "embark", "embarks",
    "paradigm", "paradigms", "multifaceted", "nuanced",
    "transformative", "revolutionary", "comprehensive", "holistic",
    "seamless", "seamlessly", "bustling",
    "treasure trove", "wealth of", "plethora", "myriad",
    "unveil", "unveils", "unveiling", "unleash", "unleashes",
    "cutting-edge", "state-of-the-art", "unprecedented",
    "groundbreaking", "renowned", "boasts", "boast",
    "innovative", "garner", "garners", "enduring", "interplay",
    "aligns with", "align with",
    "highlighting", "emphasizing", "bolstered",
    "enhance", "enhances", "enhanced",
    "pivotal", "realm", "crucial",
]

# Tier 3 — phrase regexes; block on match.
TIER3_PHRASE_PATTERNS = [
    r"it is important to note( that)?",
    r"it should be noted( that)?",
    r"it is worth mentioning",
    r"in conclusion,",
    r"\bultimately,",
    r"while it is true that",
    r"in the realm of",
    r"in the world of",
    r"in the era of",
    r"plays?\s+an?\s+(crucial|pivotal|key)\s+role",
    r"^(Furthermore|Moreover|Additionally|Notably|Importantly|Interestingly|Remarkably|Fascinatingly),",
    r"^(Certainly|Absolutely|Of course),",
    r"studies have shown",
    r"research indicates",
    r"experts agree",
    r"it is widely accepted",
    r"it is well established",
]

# Disciplinary exemptions: tier-2 word + this regex anywhere = ignore that hit.
EXEMPTIONS = {
    "robust": [r"\brobust regression\b", r"\brobust stability\b",
               r"\brobust standard error", r"\brobust optimization\b"],
    "comprehensive": [r"\bcomprehensive search (strategy|protocol)\b",
                      r"\bsystematic review\b"],
    "novel": [r"\bsee Appendix\b", r"\bsearch protocol\b",
              r"\bto our knowledge\b"],
    "crucial": [r"crucial (Ser|Thr|Tyr|Lys)\d+",  # phosphorylation site
                r"crucial phosphorylation"],
}


def _split_paragraphs(text: str) -> list:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def lint_text(text: str) -> dict:
    """Returns dict with hits[] and style metrics."""
    hits = []
    paragraphs = _split_paragraphs(text)
    sections = [text]  # treated as one section unless caller pre-splits

    # Tier 1 — first hit blocks
    for term in TIER1_BLACKLIST:
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            # Check exemption
            if any(re.search(p, text, re.IGNORECASE)
                   for p in EXEMPTIONS.get(term, [])):
                continue
            hits.append({
                "tier": 1, "term": term, "start": m.start(), "end": m.end(),
                "match": m.group(0),
                "rationale": "Empirically excessive in post-ChatGPT corpora (Liang et al. 2024).",
            })

    # Tier 2 — count per section; flag if ≥2
    for section in sections:
        per_term_count = {}
        per_term_matches = {}
        for term in TIER2_BLACKLIST:
            if term in EXEMPTIONS:
                # Skip if exempted in context
                if any(re.search(p, section, re.IGNORECASE)
                       for p in EXEMPTIONS[term]):
                    continue
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            ms = list(pattern.finditer(section))
            if ms:
                per_term_count[term] = len(ms)
                per_term_matches[term] = ms
        for term, cnt in per_term_count.items():
            if cnt >= 2:
                for m in per_term_matches[term]:
                    hits.append({
                        "tier": 2, "term": term, "start": m.start(),
                        "end": m.end(), "match": m.group(0),
                        "rationale": f"Tier-2 LLM-style word; {cnt} occurrences in section (≥2 threshold).",
                    })

    # Tier 3 — phrase regex
    for pat in TIER3_PHRASE_PATTERNS:
        rx = re.compile(pat, re.IGNORECASE | re.MULTILINE)
        for m in rx.finditer(text):
            hits.append({
                "tier": 3, "term": pat, "start": m.start(), "end": m.end(),
                "match": m.group(0),
                "rationale": "Tier-3 phrase pattern (filler / sycophantic / authority surrogate).",
            })

    return {"hits": hits, "paragraph_count": len(paragraphs)}
