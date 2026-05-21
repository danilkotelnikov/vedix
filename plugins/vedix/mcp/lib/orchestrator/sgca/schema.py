from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

NODE_TYPES = frozenset({"claim", "method", "result", "limitation", "entity", "paper", "author"})
EDGE_KINDS_WITHIN_TRACK = frozenset({
    "contains", "cites", "extends", "contradicts",
    "uses_method", "limited_by", "supports", "derives_from",
})
EDGE_KINDS_CROSS_TRACK = frozenset({"confirms", "contests", "independently_supports"})
ALL_EDGE_KINDS = EDGE_KINDS_WITHIN_TRACK | EDGE_KINDS_CROSS_TRACK

NodeId = str  # e.g. "smith2024.claim01", "method:DFT_b3lyp", "concept:frontier_orbital_energy"
ByteRange = tuple[int, int]


class Provenance(BaseModel):
    extractor_model: str
    extractor_ts: float


class RawPointer(BaseModel):
    pdf: Optional[str] = None
    text: str
    jats: Optional[str] = None
    byte_len: int = Field(ge=0)


class Author(BaseModel):
    id: NodeId
    name: str
    orcid: Optional[str] = None


class Entity(BaseModel):
    id: NodeId
    canonical_term: str
    lattice_link: Optional[NodeId] = None


class Method(BaseModel):
    id: NodeId
    type: Literal["computational", "experimental", "analytical", "theoretical", "review"]
    paraphrase: str
    verbatim_quote: str
    quote_byte_range: list[int]
    page: int
    section: str

    @field_validator("quote_byte_range")
    @classmethod
    def _validate_range(cls, v: list[int]) -> list[int]:
        if len(v) != 2 or v[0] < 0 or v[1] <= v[0]:
            raise ValueError(f"quote_byte_range must be [start, end] with 0 <= start < end (got {v})")
        return v


class Result(BaseModel):
    id: NodeId
    paraphrase: str
    backs_claim: NodeId


class Limitation(BaseModel):
    id: NodeId
    paraphrase: str


class Claim(BaseModel):
    id: NodeId
    type: Literal["empirical", "methodological", "review", "theoretical"]
    paraphrase: str
    verbatim_quote: str
    quote_byte_range: list[int]
    page: int
    section: str
    confidence: float = Field(ge=0.0, le=1.0)
    hedge: bool
    entities: list[NodeId] = Field(default_factory=list)
    methods: list[NodeId] = Field(default_factory=list)
    limitations: list[NodeId] = Field(default_factory=list)
    provenance: Provenance

    @field_validator("quote_byte_range")
    @classmethod
    def _validate_range(cls, v: list[int]) -> list[int]:
        if len(v) != 2 or v[0] < 0 or v[1] <= v[0]:
            raise ValueError(f"quote_byte_range must be [start, end] with 0 <= start < end (got {v})")
        return v


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: NodeId = Field(alias="from")
    to: NodeId
    kind: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("kind")
    @classmethod
    def _kind_in_closed_set(cls, v: str) -> str:
        if v not in ALL_EDGE_KINDS:
            raise ValueError(f"unknown edge kind {v!r}; expected one of {sorted(ALL_EDGE_KINDS)}")
        return v


class Paper(BaseModel):
    id: NodeId
    doi: str
    title: str
    year: int
    venue: Optional[str] = None
    language: str


class KGNodes(BaseModel):
    claims: list[Claim] = Field(default_factory=list)
    methods: list[Method] = Field(default_factory=list)
    results: list[Result] = Field(default_factory=list)
    limitations: list[Limitation] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)


class KGFragment(BaseModel):
    paper_id: str
    doi: str
    title: str
    year: int
    authors: list[Author]
    venue: Optional[str] = None
    language: str
    license: str
    raw_pointer: RawPointer
    nodes: KGNodes
    edges: list[Edge] = Field(default_factory=list)


class ConceptLatticeEntry(BaseModel):
    id: NodeId
    canonical_label_en: str
    canonical_label_ru: Optional[str] = None
    alt_labels: list[str] = Field(default_factory=list)
    broader: list[NodeId] = Field(default_factory=list)
    narrower: list[NodeId] = Field(default_factory=list)
    related: list[NodeId] = Field(default_factory=list)
    appears_in_papers: list[str] = Field(default_factory=list)
    appearance_count: int = 0
    drift_warning: bool = False


class Anchor(BaseModel):
    node_id: NodeId
    # Three canonical roles per SGCA §3.3:
    #   primary  -> cite-bucket sentences (single dominant source claim)
    #   support  -> synthesize-bucket sentences (>=2 anchors, each contributes)
    #   contrast -> optional, for sentences that explicitly compare against a source
    anchor_role: Literal["primary", "support", "contrast"]


class VerifierResult(BaseModel):
    status: Literal["pass", "fail-entailment", "fail-bucket", "pending-user-approval", "verification_pending"]
    entailment_score: Optional[float] = None
    synthesis_check: Optional[Literal["pass", "trivial-restatement", "unsupported"]] = None
    rationale: str = ""
    ran_at_ts: float = 0.0


class SpeculationAuthorization(BaseModel):
    source: Literal["setup_form", "user_live_approval"]
    authorized_at: float
    authorized_by: str


class SentenceBucket(BaseModel):
    sentence_id: str
    text: str
    bucket: Literal["cite", "synthesize", "speculate"]
    anchors: list[Anchor] = Field(default_factory=list)
    evidence_path: Optional[str] = None
    hedge_language: Optional[str] = None
    authorization: Optional[SpeculationAuthorization] = None
    verifier: Optional[VerifierResult] = None

    @field_validator("anchors")
    @classmethod
    def _anchors_required_per_bucket(cls, v, info):
        bucket = info.data.get("bucket")
        if bucket == "cite" and len(v) < 1:
            raise ValueError("bucket=cite requires at least 1 anchor")
        if bucket == "synthesize" and len(v) < 2:
            raise ValueError("bucket=synthesize requires at least 2 anchors")
        return v


class AllowedSet(BaseModel):
    paragraph_id: str
    paragraph_topic: str
    nodes: list[NodeId]
    max_size: int = 30
    kg_revision_id: str
