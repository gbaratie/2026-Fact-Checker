from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.models import Article, Candidate, IngestionRun, Interview, ParliamentaryVote
from app.schemas import (
    ArticleOut,
    CandidateDetailOut,
    CandidateOut,
    HealthOut,
    IngestionRunOut,
    InterviewOut,
    PaginatedResponse,
    ParliamentaryVoteOut,
)

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)) -> HealthOut:
    try:
        await db.execute(select(1))
        return HealthOut(status="ok", database="connected")
    except Exception:
        return HealthOut(status="degraded", database="disconnected")


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(db: AsyncSession = Depends(get_db)) -> list[Candidate]:
    result = await db.execute(select(Candidate).order_by(Candidate.full_name))
    return list(result.scalars().all())


@router.get("/candidates/{slug}", response_model=CandidateDetailOut)
async def get_candidate(slug: str, db: AsyncSession = Depends(get_db)) -> CandidateDetailOut:
    result = await db.execute(select(Candidate).where(Candidate.slug == slug))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")

    interview_count = await db.scalar(
        select(func.count()).select_from(Interview).where(Interview.candidate_id == candidate.id)
    )
    vote_count = await db.scalar(
        select(func.count())
        .select_from(ParliamentaryVote)
        .where(ParliamentaryVote.candidate_id == candidate.id)
    )
    article_count = await db.scalar(
        select(func.count()).select_from(Article).where(Article.candidate_id == candidate.id)
    )

    return CandidateDetailOut(
        id=candidate.id,
        slug=candidate.slug,
        full_name=candidate.full_name,
        party=candidate.party,
        external_ids=candidate.external_ids or {},
        status=candidate.status,
        interview_count=interview_count or 0,
        vote_count=vote_count or 0,
        article_count=article_count or 0,
    )


def _paginate(total: int, page: int, page_size: int, items: list) -> PaginatedResponse:
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/candidates/{slug}/interviews", response_model=PaginatedResponse)
async def list_interviews(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    candidate = await _get_candidate_or_404(db, slug)
    total = await db.scalar(
        select(func.count()).select_from(Interview).where(Interview.candidate_id == candidate.id)
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Interview)
        .options(selectinload(Interview.source))
        .where(Interview.candidate_id == candidate.id)
        .order_by(Interview.published_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    items = [InterviewOut.model_validate(i) for i in result.scalars().all()]
    return _paginate(total or 0, page, page_size, items)


@router.get("/candidates/{slug}/votes", response_model=PaginatedResponse)
async def list_votes(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    candidate = await _get_candidate_or_404(db, slug)
    total = await db.scalar(
        select(func.count())
        .select_from(ParliamentaryVote)
        .where(ParliamentaryVote.candidate_id == candidate.id)
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ParliamentaryVote)
        .options(selectinload(ParliamentaryVote.source))
        .where(ParliamentaryVote.candidate_id == candidate.id)
        .order_by(ParliamentaryVote.vote_date.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    items = [ParliamentaryVoteOut.model_validate(v) for v in result.scalars().all()]
    return _paginate(total or 0, page, page_size, items)


@router.get("/candidates/{slug}/articles", response_model=PaginatedResponse)
async def list_articles(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    candidate = await _get_candidate_or_404(db, slug)
    total = await db.scalar(
        select(func.count()).select_from(Article).where(Article.candidate_id == candidate.id)
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.source))
        .where(Article.candidate_id == candidate.id)
        .order_by(Article.published_at.desc().nullslast())
        .offset(offset)
        .limit(page_size)
    )
    items = [ArticleOut.model_validate(a) for a in result.scalars().all()]
    return _paginate(total or 0, page, page_size, items)


@router.get("/ingestion/runs", response_model=list[IngestionRunOut])
async def list_ingestion_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionRun]:
    result = await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.post("/ingestion/trigger", response_model=IngestionRunOut)
async def trigger_ingestion(
    x_ingestion_secret: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> IngestionRun:
    if x_ingestion_secret != settings.ingestion_secret:
        raise HTTPException(status_code=403, detail="Secret invalide")

    from app.ingestion.orchestrator import IngestionOrchestrator

    orchestrator = IngestionOrchestrator(db)
    return await orchestrator.run()


async def _get_candidate_or_404(db: AsyncSession, slug: str) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.slug == slug))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    return candidate
