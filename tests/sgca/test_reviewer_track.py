import pytest
from unittest.mock import AsyncMock, patch
from plugins.vedix.mcp.lib.orchestrator.sgca.reviewer_track import (
    ReviewerTrack, ReviewerVerdict,
)
from plugins.vedix.mcp.lib.orchestrator.sgca.kg_store import KGStore, Tier
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    KGFragment, KGNodes, Claim, Author, RawPointer, Provenance,
)


def _seed(store, paper_id, claim_paraphrase):
    store.write_paper(KGFragment(
        paper_id=paper_id, doi=f"10/{paper_id}", title=paper_id, year=2024,
        authors=[Author(id=f"author:{paper_id}", name=paper_id)],
        language="en", license="CC-BY",
        raw_pointer=RawPointer(text=f"raw/{paper_id}.txt", byte_len=10),
        nodes=KGNodes(claims=[
            Claim(id=f"{paper_id}.c1", type="empirical", paraphrase=claim_paraphrase,
                  verbatim_quote=claim_paraphrase, quote_byte_range=[0, len(claim_paraphrase)],
                  page=1, section="Results", confidence=0.9, hedge=False,
                  provenance=Provenance(extractor_model="x", extractor_ts=0)),
        ]),
        edges=[],
    ))


@pytest.mark.asyncio
async def test_reviewer_confirms_when_independent_evidence_agrees(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    writer = KGStore(tier=Tier.JOB, scope_id="job_w")
    _seed(writer, "smith2024", "X correlates with Y (r=0.78)")
    reviewer = KGStore(tier=Tier.REVIEWER, scope_id="1__job_w")
    _seed(reviewer, "jones2022", "X correlates with Y (r=0.74)")  # agrees

    track = ReviewerTrack(reviewer_id="1", writer_store=writer, reviewer_store=reviewer)

    fake_judge = AsyncMock(return_value={"verdict": "independently_confirmed",
                                         "supporting_anchors_R": [{"node_id": "jones2022.c1",
                                                                    "paper": "jones2022",
                                                                    "agreement": "full"}],
                                         "counter_anchors_R": [],
                                         "rationale": "Jones 2022 reports same trend"})
    with patch.object(track, "_llm_confront", new=fake_judge):
        review = await track.confront_headlines(headline_claim_ids=["smith2024.c1"])
    assert len(review.per_claim) == 1
    assert review.per_claim[0]["verdict"] == "independently_confirmed"


@pytest.mark.asyncio
async def test_reviewer_contests_when_evidence_opposes(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    writer = KGStore(tier=Tier.JOB, scope_id="job_w2")
    _seed(writer, "smith2024", "X correlates with Y (r=0.78)")
    reviewer = KGStore(tier=Tier.REVIEWER, scope_id="1__job_w2")
    _seed(reviewer, "kim2024", "X does NOT correlate with Y for electron-rich systems")

    track = ReviewerTrack(reviewer_id="1", writer_store=writer, reviewer_store=reviewer)
    fake_judge = AsyncMock(return_value={"verdict": "contested",
                                         "supporting_anchors_R": [],
                                         "counter_anchors_R": [{"node_id": "kim2024.c1",
                                                                 "paper": "kim2024",
                                                                 "contradiction": "opposite trend"}],
                                         "rationale": "Kim 2024 reports opposite"})
    with patch.object(track, "_llm_confront", new=fake_judge):
        review = await track.confront_headlines(headline_claim_ids=["smith2024.c1"])
    assert review.per_claim[0]["verdict"] == "contested"
    assert review.n_contested == 1


@pytest.mark.asyncio
async def test_reviewer_unsupported_when_no_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    writer = KGStore(tier=Tier.JOB, scope_id="job_w3")
    _seed(writer, "smith2024", "X correlates with Y (r=0.78)")
    reviewer = KGStore(tier=Tier.REVIEWER, scope_id="1__job_w3")  # empty

    track = ReviewerTrack(reviewer_id="1", writer_store=writer, reviewer_store=reviewer)
    fake_judge = AsyncMock(return_value={"verdict": "unsupported_by_R",
                                         "supporting_anchors_R": [],
                                         "counter_anchors_R": [],
                                         "investigation_notes": "No relevant papers found"})
    with patch.object(track, "_llm_confront", new=fake_judge):
        review = await track.confront_headlines(headline_claim_ids=["smith2024.c1"])
    assert review.per_claim[0]["verdict"] == "unsupported_by_R"


def test_merge_reviewer_kg_into_project_dedups_by_doi(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    reviewer = KGStore(tier=Tier.REVIEWER, scope_id="1__job_x")
    project = KGStore(tier=Tier.PROJECT, scope_id="proj_x")
    _seed(reviewer, "shared_paper", "x")
    _seed(project, "shared_paper", "x")
    _seed(reviewer, "new_to_reviewer", "y")

    from plugins.vedix.mcp.lib.orchestrator.sgca.reviewer_track import merge_reviewer_into_project
    merge_reviewer_into_project(reviewer_store=reviewer, project_store=project)
    project_papers = set(project.list_paper_ids())
    assert "shared_paper" in project_papers
    assert "new_to_reviewer" in project_papers
