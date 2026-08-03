from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_type: str
    url: str
    publisher: str | None
    fetched_at: datetime
    raw_metadata: dict = {}


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    full_name: str
    party: str | None
    external_ids: dict
    status: str


class CandidateDetailOut(CandidateOut):
    interview_count: int = 0
    program_count: int = 0
    vote_count: int = 0
    article_count: int = 0


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
    vote_date: datetime | None
    source: SourceOut


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
