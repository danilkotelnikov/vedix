from __future__ import annotations
import json
from dataclasses import dataclass, field
from ..dispatch import dispatch_agent
from .kg_store import KGStore


@dataclass
class ReviewerVerdict:
    reviewer_id: str
    n_papers_independently_pulled: int
    overlap_with_writer_set: int
    new_to_reviewer: int
    per_claim: list[dict] = field(default_factory=list)
    n_confirmed: int = 0
    n_independently_confirmed: int = 0
    n_contested: int = 0
    n_unsupported_by_R: int = 0


class ReviewerTrack:
    def __init__(self, *, reviewer_id: str, writer_store: KGStore, reviewer_store: KGStore):
        self.reviewer_id = reviewer_id
        self.writer_store = writer_store
        self.reviewer_store = reviewer_store

    async def confront_headlines(self, *, headline_claim_ids: list[str]) -> ReviewerVerdict:
        writer_papers = set(self.writer_store.list_paper_ids())
        reviewer_papers = set(self.reviewer_store.list_paper_ids())
        verdict = ReviewerVerdict(
            reviewer_id=self.reviewer_id,
            n_papers_independently_pulled=len(reviewer_papers),
            overlap_with_writer_set=len(writer_papers & reviewer_papers),
            new_to_reviewer=len(reviewer_papers - writer_papers),
        )
        for cid in headline_claim_ids:
            writer_claim = self._find_claim(self.writer_store, cid)
            if writer_claim is None:
                continue
            judgment = await self._llm_confront(writer_claim=writer_claim)
            verdict.per_claim.append({"claim_id_in_manuscript": cid, **judgment})
            v = judgment.get("verdict")
            if v == "confirmed":
                verdict.n_confirmed += 1
            elif v == "independently_confirmed":
                verdict.n_independently_confirmed += 1
            elif v == "contested":
                verdict.n_contested += 1
            elif v == "unsupported_by_R":
                verdict.n_unsupported_by_R += 1
        return verdict

    def _find_claim(self, store: KGStore, cid: str):
        if "." not in cid:
            return None
        paper_id = cid.split(".", 1)[0]
        paper = store.read_paper(paper_id)
        if paper is None:
            return None
        for c in paper.nodes.claims:
            if c.id == cid:
                return c
        return None

    async def _llm_confront(self, *, writer_claim) -> dict:
        # Gather reviewer's claim corpus
        reviewer_corpus = []
        for pid in self.reviewer_store.list_paper_ids():
            paper = self.reviewer_store.read_paper(pid)
            if paper is None:
                continue
            for c in paper.nodes.claims:
                reviewer_corpus.append({"id": c.id, "paper": pid,
                                        "paraphrase": c.paraphrase,
                                        "quote": c.verbatim_quote})
        prompt = (
            "You are an adversarial peer reviewer. Compare this WRITER CLAIM against "
            "your INDEPENDENTLY-PULLED REVIEWER CORPUS. Decide if the corpus supports, "
            "contests, or fails to address the claim.\n\n"
            f"WRITER CLAIM:\n  id: {writer_claim.id}\n  paraphrase: {writer_claim.paraphrase}\n"
            f"  verbatim: \"{writer_claim.verbatim_quote}\"\n\n"
            f"REVIEWER CORPUS (your independent finds):\n{json.dumps(reviewer_corpus, indent=2)}\n\n"
            "Reply ONLY with JSON:\n"
            '{"verdict": "confirmed" | "independently_confirmed" | "contested" | "unsupported_by_R" | "partial",\n'
            ' "supporting_anchors_R": [{"node_id": "...", "paper": "...", "agreement": "full|partial|weaker_effect"}],\n'
            ' "counter_anchors_R":    [{"node_id": "...", "paper": "...", "contradiction": "..."}],\n'
            ' "rationale": "<one sentence>"}'
        )
        resp = await dispatch_agent(agent_type="claim-verifier", prompt=prompt, max_tokens=2048)
        try:
            return json.loads(resp.content)
        except Exception:
            return {"verdict": "unsupported_by_R",
                    "supporting_anchors_R": [], "counter_anchors_R": [],
                    "rationale": "reviewer output unparseable"}


def merge_reviewer_into_project(*, reviewer_store: KGStore, project_store: KGStore) -> int:
    """Merge reviewer KG into project tier. Papers deduped by paper_id (DOI proxy).
    Returns count of newly-added papers."""
    existing = set(project_store.list_paper_ids())
    added = 0
    for pid in reviewer_store.list_paper_ids():
        if pid in existing:
            continue
        frag = reviewer_store.read_paper(pid)
        if frag is not None:
            project_store.write_paper(frag)
            added += 1
    return added
