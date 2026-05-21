"""SGCA §8.3 — 500-pair labeled benchmark.
   Production gate: false_positive_rate < 2% (unsupported sentences must not be
   accepted as 'pass'). False negatives (entailed-but-rejected) are tolerated
   since they trigger rewrites, not silent acceptance."""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from plugins.vedix.mcp.lib.orchestrator.sgca.claim_verifier import ClaimVerifier
from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    KGFragment, KGNodes, Claim, Author, RawPointer, Provenance,
    SentenceBucket, Anchor,
)

PAIRS_FILE = Path(__file__).parent.parent / "gold_set" / "verifier_pairs.jsonl"


@pytest.mark.skipif(not PAIRS_FILE.exists(),
                    reason=f"verifier benchmark pairs not yet curated at {PAIRS_FILE}")
@pytest.mark.asyncio
async def test_verifier_meets_false_positive_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    pairs = [json.loads(l) for l in PAIRS_FILE.read_text(encoding="utf-8").splitlines() if l]
    fp = 0  # false positives: gold=unsupported, verifier=pass
    fn = 0
    tp = 0
    tn = 0
    store = KGStore(tier=Tier.JOB, scope_id="bench_va")
    # Seed claims from gold-set
    for p in pairs:
        store.write_paper(KGFragment(
            paper_id=p["paper_id"], doi=p["paper_id"], title="t", year=2024,
            authors=[Author(id=f"author:{p['paper_id']}", name=p["paper_id"])],
            language="en", license="CC-BY",
            raw_pointer=RawPointer(text=f"raw/{p['paper_id']}.txt", byte_len=len(p["anchor_quote"])),
            nodes=KGNodes(claims=[
                Claim(id=p["anchor_id"], type="empirical", paraphrase=p["anchor_paraphrase"],
                      verbatim_quote=p["anchor_quote"],
                      quote_byte_range=[0, len(p["anchor_quote"])],
                      page=1, section="Results", confidence=0.9, hedge=False,
                      provenance=Provenance(extractor_model="x", extractor_ts=0)),
            ]),
            edges=[],
        ))
    verifier = ClaimVerifier(store=store)
    # In real CI, this runs against a live LLM; here we accept a stubbed verifier
    # signal that the benchmark exists and can be wired up.
    for p in pairs:
        sentence = SentenceBucket(
            sentence_id="s",
            text=p["sentence"],
            bucket="cite",
            anchors=[Anchor(node_id=p["anchor_id"], anchor_role="primary")],
        )
        result = await verifier.verify(sentence)
        gold_pass = p["gold_label"] == "entailed"
        verifier_pass = result.verifier.status == "pass"
        if gold_pass and verifier_pass:
            tp += 1
        elif not gold_pass and not verifier_pass:
            tn += 1
        elif not gold_pass and verifier_pass:
            fp += 1
        elif gold_pass and not verifier_pass:
            fn += 1
    fpr = fp / max(1, fp + tn)
    fnr = fn / max(1, fn + tp)
    print(f"verifier accuracy: FP={fp} FN={fn} TP={tp} TN={tn} FPR={fpr:.4f} FNR={fnr:.4f}")
    assert fpr < 0.02, f"false positive rate {fpr:.4f} exceeds 0.02 production gate"
