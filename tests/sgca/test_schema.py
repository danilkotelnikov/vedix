import pytest
from pydantic import ValidationError
from plugins.vedix.mcp.lib.orchestrator.sgca.schema import (
    Claim, Method, Result, Limitation, Entity, Paper, Author, Edge,
    KGFragment, ConceptLatticeEntry, SentenceBucket, AllowedSet,
    EDGE_KINDS_WITHIN_TRACK, EDGE_KINDS_CROSS_TRACK, NODE_TYPES,
)


def test_node_and_edge_types_are_closed():
    assert NODE_TYPES == {"claim", "method", "result", "limitation", "entity", "paper", "author"}
    assert EDGE_KINDS_WITHIN_TRACK == {"contains", "cites", "extends", "contradicts", "uses_method", "limited_by", "supports", "derives_from"}
    assert EDGE_KINDS_CROSS_TRACK == {"confirms", "contests", "independently_supports"}


def test_claim_requires_verbatim_quote_and_byte_range():
    with pytest.raises(ValidationError):
        Claim(id="x.c1", type="empirical", paraphrase="p", page=1, section="Results",
              confidence=0.9, hedge=False, entities=[], methods=[], limitations=[],
              provenance={"extractor_model": "x", "extractor_ts": 0})
    c = Claim(id="x.c1", type="empirical", paraphrase="p",
              verbatim_quote="abc", quote_byte_range=[0, 3],
              page=1, section="Results", confidence=0.9, hedge=False,
              entities=[], methods=[], limitations=[],
              provenance={"extractor_model": "x", "extractor_ts": 0})
    assert c.verbatim_quote == "abc"


def test_claim_byte_range_validates_pair():
    with pytest.raises(ValidationError):
        Claim(id="x.c1", type="empirical", paraphrase="p",
              verbatim_quote="abc", quote_byte_range=[10, 5],   # end < start
              page=1, section="Results", confidence=0.9, hedge=False,
              entities=[], methods=[], limitations=[],
              provenance={"extractor_model": "x", "extractor_ts": 0})


def test_edge_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        Edge(from_="a", to="b", kind="invented_kind")


def test_sentence_bucket_three_values():
    SentenceBucket(sentence_id="s1", text="x", bucket="cite", anchors=[{"node_id": "a", "anchor_role": "primary"}])
    SentenceBucket(sentence_id="s1", text="x", bucket="synthesize", anchors=[
        {"node_id": "a", "anchor_role": "support"}, {"node_id": "b", "anchor_role": "support"}])
    SentenceBucket(sentence_id="s1", text="x", bucket="speculate", anchors=[],
                   hedge_language="we hypothesize that",
                   authorization={"source": "setup_form", "authorized_at": 0, "authorized_by": "me@x"})
    with pytest.raises(ValidationError):
        SentenceBucket(sentence_id="s1", text="x", bucket="invented", anchors=[])


def test_kg_fragment_validates_full():
    frag = KGFragment(
        paper_id="smith2024",
        doi="10.1/x",
        title="t",
        year=2024,
        authors=[Author(id="author:s", name="Smith")],
        venue="J",
        language="en",
        license="CC-BY",
        raw_pointer={"pdf": "raw/x.pdf", "text": "raw/x.txt", "byte_len": 100},
        nodes={"claims": [], "methods": [], "results": [], "limitations": [], "entities": []},
        edges=[],
    )
    assert frag.paper_id == "smith2024"
