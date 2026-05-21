"""Stage 9 — stratified train/val/test split with no paper leakage.

We split at the *paper* level (not the paragraph level) so that a paper
whose paragraphs appear in train can never also appear in val/test.
This is critical: paragraph-level splits routinely leak topical bigrams
and inflate validation F1 by 5-10 points.
"""
from __future__ import annotations

import random
from collections import defaultdict


def stratified_split_by_paper(
    data: list[dict],
    *,
    val_frac: float = 0.1,
    test_frac: float = 0.1,
    seed: int = 42,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Shuffle papers (not paragraphs) and slice into train/val/test.

    Returns three paragraph lists. Caller must ensure each record has a
    ``paper_id`` key.
    """
    rng = random.Random(seed)
    by_paper: dict[str, list[dict]] = defaultdict(list)
    for d in data:
        by_paper[d["paper_id"]].append(d)

    papers = list(by_paper)
    rng.shuffle(papers)
    n = len(papers)
    n_val = max(1, int(n * val_frac))
    n_test = max(1, int(n * test_frac))
    val_pids = set(papers[:n_val])
    test_pids = set(papers[n_val : n_val + n_test])

    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for pid, samples in by_paper.items():
        bucket = val if pid in val_pids else (test if pid in test_pids else train)
        bucket.extend(samples)
    return train, val, test
