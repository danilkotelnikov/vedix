"""Stage 10 — summarise the prepared corpus.

Writes ``corpus_stats.json`` for the (discipline, language) pair with
per-split counts, class balance, and mean paragraph length. This is the
file ``vedix model publish`` consults to verify the corpus shape before
the model is uploaded.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean


def _stat_for(lst: list[dict]) -> dict:
    labels = Counter(d.get("label") for d in lst)
    lengths = [int(d.get("n_words", len(d.get("text", "").split()))) for d in lst]
    return {
        "n": len(lst),
        "class_balance": dict(labels),
        "mean_n_words": round(mean(lengths) if lengths else 0.0, 1),
    }


def compute_stats(
    *,
    train: list[dict],
    val: list[dict],
    test: list[dict],
    out: Path,
) -> dict:
    """Compute per-split summaries and write JSON to ``out``."""
    out_obj = {
        "train": _stat_for(train),
        "val": _stat_for(val),
        "test": _stat_for(test),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(out_obj, indent=2), encoding="utf-8")
    return out_obj
