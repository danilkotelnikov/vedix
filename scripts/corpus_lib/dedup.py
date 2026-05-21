"""Stage 6 — MinHashLSH near-duplicate removal.

We shingle each paragraph into 5-character grams, compute a 128-bit
MinHash, and insert into an LSH index keyed by the Jaccard threshold
(default 0.85). The first occurrence of any cluster is kept; subsequent
near-duplicates are dropped.
"""
from __future__ import annotations


def _shingles(text: str, k: int = 5) -> list[str]:
    """Return the k-shingles of ``text`` (lowercased)."""
    text = text.lower()
    if len(text) < k:
        return [text] if text else []
    return [text[i : i + k] for i in range(len(text) - k + 1)]


def _minhash(text: str, num_perm: int = 128):
    """Compute the MinHash sketch of ``text``."""
    from datasketch import MinHash  # type: ignore[import-untyped]

    m = MinHash(num_perm=num_perm)
    for s in _shingles(text):
        m.update(s.encode("utf-8"))
    return m


def dedup_minhash(
    paragraphs: list[dict],
    *,
    jaccard_threshold: float = 0.85,
    num_perm: int = 128,
) -> list[dict]:
    """Drop near-duplicate paragraphs at ``jaccard_threshold`` similarity.

    Returns the kept paragraphs in input order — first-seen wins.
    """
    from datasketch import MinHashLSH  # type: ignore[import-untyped]

    lsh = MinHashLSH(threshold=jaccard_threshold, num_perm=num_perm)
    kept: list[dict] = []
    for i, p in enumerate(paragraphs):
        mh = _minhash(p["text"], num_perm=num_perm)
        key = f"p{i}"
        if not lsh.query(mh):
            lsh.insert(key, mh)
            kept.append(p)
    return kept
