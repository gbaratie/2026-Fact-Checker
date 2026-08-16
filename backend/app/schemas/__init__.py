from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    url: str
    publisher: str | None
    fetched_at: datetime
    raw_metadata: dict = {}


class ParliamentaryGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    full_name: str
    color: str | None
    chamber: str
    legislature: int | None
    spectrum: str | None


CandidateStatus = Literal["declared", "potential", "withdrawn"]


class CandidateCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    party: str | None = Field(default=None, max_length=120)
    status: CandidateStatus = "potential"
    slug: str | None = Field(default=None, max_length=120)
    clair_slug: str | None = Field(default=None, max_length=120)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("Le nom complet est trop court")
        return stripped

    @field_validator("party", "slug", "clair_slug")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CandidateUpdate(BaseModel):
    party: str | None = Field(default=None, max_length=120)
    status: CandidateStatus | None = None
    clair_slug: str | None = Field(default=None, max_length=120)

    @field_validator("party", "clair_slug")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    full_name: str
    party: str | None
    external_ids: dict
    status: str
    parliamentary_group: ParliamentaryGroupOut | None = None


class StatsOut(BaseModel):
    candidate_count: int
    database: str
    last_ingestion_at: datetime | None = None


class SeedCandidatesOut(BaseModel):
    created: int
    updated: int
    total: int


class VoteStatsOut(BaseModel):
    total: int = 0
    pour: int = 0
    contre: int = 0
    abstention: int = 0
    other: int = 0
    with_group_position: int = 0
    aligned_with_group: int = 0
    loyalty_rate: float | None = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    label: str
    description: str | None = None
    sort_order: int = 0


class CandidateDetailOut(CandidateOut):
    interview_count: int = 0
    program_count: int = 0
    vote_count: int = 0
    article_count: int = 0
    claim_count: int = 0
    vote_stats: VoteStatsOut | None = None


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    youtube_video_id: str
    title: str
    channel_name: str | None
    transcript: str | None
    published_at: datetime | None
    source: SourceOut


class ParliamentaryVoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chamber: str
    scrutin_id: str
    title: str
    position: str
    group_position: str | None = None
    vote_date: datetime | None
    source: SourceOut
    parliamentary_group: ParliamentaryGroupOut | None = None
    topics: list[TopicOut] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def aligned_with_group(self) -> bool | None:
        if not self.group_position:
            return None
        return self.position == self.group_position


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str
    publisher: str | None
    excerpt: str | None
    published_at: datetime | None
    source: SourceOut


class ProgramDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    url: str
    kind: str
    year: int | None
    publisher: str | None
    excerpt: str | None
    note: str | None
    source: SourceOut


class GroupMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    full_name: str
    party: str | None
    status: str
    vote_count: int = 0
    vote_stats: VoteStatsOut | None = None


class ParliamentaryGroupDetailOut(ParliamentaryGroupOut):
    member_count: int = 0
    vote_count: int = 0
    vote_stats: VoteStatsOut | None = None
    members: list[GroupMemberOut] = []


class PartyOut(BaseModel):
    party: str
    candidate_count: int
    vote_count: int
    vote_stats: VoteStatsOut | None = None
    candidates: list[CandidateOut] = []


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    stats: dict
    errors: list


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class HealthOut(BaseModel):
    status: str
    database: str


ClaimStance = Literal["pour", "contre", "nuance", "inconnu"]
EvidenceType = Literal["interview", "program", "article", "manual", "other"]
ClaimMethod = Literal["manual", "llm", "rule"]
CoherenceStatus = Literal[
    "aligned",
    "conflict",
    "mixed",
    "abstention_only",
    "claims_only",
    "votes_only",
    "empty",
]


class SeedTopicsOut(BaseModel):
    created: int
    updated: int
    total: int


class ClaimCreate(BaseModel):
    topic_slug: str = Field(min_length=1, max_length=120)
    stance: ClaimStance
    summary: str = Field(min_length=3, max_length=500)
    quote: str | None = None
    evidence_type: EvidenceType = "manual"
    interview_id: UUID | None = None
    program_document_id: UUID | None = None
    article_id: UUID | None = None
    source_url: str | None = None
    method: ClaimMethod = "manual"
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("topic_slug", "summary")
    @classmethod
    def strip_required(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Champ requis vide")
        return stripped

    @field_validator("quote", "source_url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ClaimUpdate(BaseModel):
    topic_slug: str | None = Field(default=None, min_length=1, max_length=120)
    stance: ClaimStance | None = None
    summary: str | None = Field(default=None, min_length=3, max_length=500)
    quote: str | None = None
    evidence_type: EvidenceType | None = None
    interview_id: UUID | None = None
    program_document_id: UUID | None = None
    article_id: UUID | None = None
    source_url: str | None = None
    method: ClaimMethod | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("topic_slug", "summary", "quote", "source_url")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    candidate_id: UUID
    topic: TopicOut
    stance: str
    summary: str
    quote: str | None = None
    evidence_type: str
    interview_id: UUID | None = None
    program_document_id: UUID | None = None
    article_id: UUID | None = None
    source_url: str | None = None
    method: str
    confidence: float | None = None
    created_at: datetime
    updated_at: datetime


class VoteTopicSet(BaseModel):
    topic_slugs: list[str] = Field(default_factory=list)

    @field_validator("topic_slugs")
    @classmethod
    def normalize_slugs(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for slug in value:
            cleaned = slug.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen


class TopicCoherenceOut(BaseModel):
    topic: TopicOut
    status: CoherenceStatus
    claim_stances: list[str] = []
    vote_positions: list[str] = []
    claims_count: int = 0
    votes_count: int = 0


class CandidateCoherenceOut(BaseModel):
    candidate_slug: str
    topics: list[TopicCoherenceOut] = []


class LlmClassifyVotesOut(BaseModel):
    classified: int
    skipped: int
    processed: int
    errors: list[str] = []


class LlmExtractClaimsOut(BaseModel):
    created: int
    skipped: int
    programs_processed: int
    errors: list[str] = []
