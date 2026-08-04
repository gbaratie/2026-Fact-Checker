from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.models import (
    Article,
    Candidate,
    IngestionRun,
    Interview,
    ParliamentaryGroup,
    ParliamentaryVote,
    ProgramDocument,
)
from app.schemas import (
    ArticleOut,
    CandidateCreate,
    CandidateDetailOut,
    CandidateOut,
    CandidateUpdate,
    GroupMemberOut,
    HealthOut,
    IngestionRunOut,
    InterviewOut,
    PaginatedResponse,
    ParliamentaryGroupDetailOut,
    ParliamentaryGroupOut,
    ParliamentaryVoteOut,
    PartyOut,
    ProgramDocumentOut,
    SeedCandidatesOut,
    StatsOut,
    VoteStatsOut,
)
from app.services import candidates as candidate_service

router = APIRouter()


def require_ingestion_secret(x_ingestion_secret: str = Header(...)) -> None:
    if x_ingestion_secret != settings.ingestion_secret:
        raise HTTPException(status_code=403, detail="Secret invalide")


@router.get("/health", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)) -> HealthOut:
    try:
        await db.execute(select(1))
        return HealthOut(status="ok", database="connected")
    except Exception:
        return HealthOut(status="degraded", database="disconnected")


@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    """Résumé léger pour la page d'accueil (évite de charger toute la liste candidats)."""
    database = "disconnected"
    try:
        await db.execute(select(1))
        database = "connected"
    except Exception:
        return StatsOut(candidate_count=0, database=database, last_ingestion_at=None)

    candidate_count = await db.scalar(select(func.count()).select_from(Candidate)) or 0
    last_run = await db.scalar(
        select(IngestionRun.started_at).order_by(IngestionRun.started_at.desc()).limit(1)
    )
    return StatsOut(
        candidate_count=int(candidate_count),
        database=database,
        last_ingestion_at=last_run,
    )


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(db: AsyncSession = Depends(get_db)) -> list[CandidateOut]:
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.parliamentary_group))
        .order_by(Candidate.full_name)
    )
    return [CandidateOut.model_validate(c) for c in result.scalars().all()]


@router.post(
    "/candidates",
    response_model=CandidateOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_ingestion_secret)],
)
async def create_candidate(
    payload: CandidateCreate,
    db: AsyncSession = Depends(get_db),
) -> CandidateOut:
    try:
        candidate = await candidate_service.create_candidate(db, payload)
    except LookupError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CandidateOut.model_validate(candidate)


@router.patch(
    "/candidates/{slug}",
    response_model=CandidateOut,
    dependencies=[Depends(require_ingestion_secret)],
)
async def update_candidate(
    slug: str,
    payload: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
) -> CandidateOut:
    try:
        candidate = await candidate_service.update_candidate(db, slug, payload)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CandidateOut.model_validate(candidate)


@router.delete(
    "/candidates/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_ingestion_secret)],
)
async def delete_candidate(slug: str, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await candidate_service.delete_candidate(db, slug)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/admin/seed-candidates",
    response_model=SeedCandidatesOut,
    dependencies=[Depends(require_ingestion_secret)],
)
async def seed_candidates_endpoint() -> SeedCandidatesOut:
    stats = await candidate_service.import_seed_candidates()
    return SeedCandidatesOut(**stats)


@router.get("/candidates/{slug}", response_model=CandidateDetailOut)
async def get_candidate(slug: str, db: AsyncSession = Depends(get_db)) -> CandidateDetailOut:
    result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.parliamentary_group))
        .where(Candidate.slug == slug)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")

    counts = (
        await db.execute(
            select(
                select(func.count())
                .select_from(Interview)
                .where(Interview.candidate_id == candidate.id)
                .scalar_subquery()
                .label("interviews"),
                select(func.count())
                .select_from(ProgramDocument)
                .where(ProgramDocument.candidate_id == candidate.id)
                .scalar_subquery()
                .label("programs"),
                select(func.count())
                .select_from(ParliamentaryVote)
                .where(ParliamentaryVote.candidate_id == candidate.id)
                .scalar_subquery()
                .label("votes"),
                select(func.count())
                .select_from(Article)
                .where(Article.candidate_id == candidate.id)
                .scalar_subquery()
                .label("articles"),
            )
        )
    ).one()
    vote_stats = await _vote_stats_for_filter(
        db, ParliamentaryVote.candidate_id == candidate.id
    )

    return CandidateDetailOut(
        id=candidate.id,
        slug=candidate.slug,
        full_name=candidate.full_name,
        party=candidate.party,
        external_ids=candidate.external_ids or {},
        status=candidate.status,
        parliamentary_group=(
            ParliamentaryGroupOut.model_validate(candidate.parliamentary_group)
            if candidate.parliamentary_group
            else None
        ),
        interview_count=int(counts.interviews or 0),
        program_count=int(counts.programs or 0),
        vote_count=int(counts.votes or 0),
        article_count=int(counts.articles or 0),
        vote_stats=vote_stats,
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
    page_size: int = Query(50, ge=1, le=200),
    chamber: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    candidate = await _get_candidate_or_404(db, slug)
    filters = [ParliamentaryVote.candidate_id == candidate.id]
    if chamber:
        filters.append(ParliamentaryVote.chamber == chamber)
    total = await db.scalar(
        select(func.count()).select_from(ParliamentaryVote).where(*filters)
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ParliamentaryVote)
        .options(
            selectinload(ParliamentaryVote.source),
            selectinload(ParliamentaryVote.parliamentary_group),
        )
        .where(*filters)
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


@router.get("/candidates/{slug}/programs", response_model=PaginatedResponse)
async def list_programs(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse:
    candidate = await _get_candidate_or_404(db, slug)
    total = await db.scalar(
        select(func.count())
        .select_from(ProgramDocument)
        .where(ProgramDocument.candidate_id == candidate.id)
    )
    offset = (page - 1) * page_size
    result = await db.execute(
        select(ProgramDocument)
        .options(selectinload(ProgramDocument.source))
        .where(ProgramDocument.candidate_id == candidate.id)
        .order_by(ProgramDocument.year.desc().nullslast(), ProgramDocument.title)
        .offset(offset)
        .limit(page_size)
    )
    items = [ProgramDocumentOut.model_validate(p) for p in result.scalars().all()]
    return _paginate(total or 0, page, page_size, items)


@router.get("/groups", response_model=list[ParliamentaryGroupDetailOut])
async def list_groups(db: AsyncSession = Depends(get_db)) -> list[ParliamentaryGroupDetailOut]:
    result = await db.execute(
        select(ParliamentaryGroup).order_by(ParliamentaryGroup.chamber, ParliamentaryGroup.name)
    )
    groups = list(result.scalars().all())
    if not groups:
        return []

    group_ids = [g.id for g in groups]
    member_rows = await db.execute(
        select(Candidate.parliamentary_group_id, func.count())
        .where(Candidate.parliamentary_group_id.in_(group_ids))
        .group_by(Candidate.parliamentary_group_id)
    )
    member_map = {gid: int(cnt) for gid, cnt in member_rows.all()}

    vote_rows = await db.execute(
        select(ParliamentaryVote.parliamentary_group_id, func.count())
        .where(ParliamentaryVote.parliamentary_group_id.in_(group_ids))
        .group_by(ParliamentaryVote.parliamentary_group_id)
    )
    vote_map = {gid: int(cnt) for gid, cnt in vote_rows.all()}

    out: list[ParliamentaryGroupDetailOut] = []
    for group in groups:
        vote_stats = await _vote_stats_for_filter(
            db, ParliamentaryVote.parliamentary_group_id == group.id
        )
        out.append(
            ParliamentaryGroupDetailOut(
                id=group.id,
                slug=group.slug,
                name=group.name,
                full_name=group.full_name,
                color=group.color,
                chamber=group.chamber,
                legislature=group.legislature,
                spectrum=group.spectrum,
                member_count=member_map.get(group.id, 0),
                vote_count=vote_map.get(group.id, 0),
                vote_stats=vote_stats,
                members=[],
            )
        )
    return out


@router.get("/groups/{slug}", response_model=ParliamentaryGroupDetailOut)
async def get_group(slug: str, db: AsyncSession = Depends(get_db)) -> ParliamentaryGroupDetailOut:
    result = await db.execute(
        select(ParliamentaryGroup).where(ParliamentaryGroup.slug == slug)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Groupe introuvable")

    members_result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.parliamentary_group))
        .where(Candidate.parliamentary_group_id == group.id)
        .order_by(Candidate.full_name)
    )
    members = list(members_result.scalars().all())
    member_outs: list[GroupMemberOut] = []
    for member in members:
        vote_count = await db.scalar(
            select(func.count())
            .select_from(ParliamentaryVote)
            .where(ParliamentaryVote.candidate_id == member.id)
        )
        member_outs.append(
            GroupMemberOut(
                id=member.id,
                slug=member.slug,
                full_name=member.full_name,
                party=member.party,
                status=member.status,
                vote_count=vote_count or 0,
                vote_stats=await _vote_stats_for_filter(
                    db, ParliamentaryVote.candidate_id == member.id
                ),
            )
        )

    vote_count = await db.scalar(
        select(func.count())
        .select_from(ParliamentaryVote)
        .where(ParliamentaryVote.parliamentary_group_id == group.id)
    )
    return ParliamentaryGroupDetailOut(
        id=group.id,
        slug=group.slug,
        name=group.name,
        full_name=group.full_name,
        color=group.color,
        chamber=group.chamber,
        legislature=group.legislature,
        spectrum=group.spectrum,
        member_count=len(members),
        vote_count=vote_count or 0,
        vote_stats=await _vote_stats_for_filter(
            db, ParliamentaryVote.parliamentary_group_id == group.id
        ),
        members=member_outs,
    )


@router.get("/parties", response_model=list[PartyOut])
async def list_parties(db: AsyncSession = Depends(get_db)) -> list[PartyOut]:
    """Vue agrégée par parti politique (champ candidats.party)."""
    parties_result = await db.execute(
        select(Candidate.party)
        .where(Candidate.party.is_not(None))
        .distinct()
        .order_by(Candidate.party)
    )
    parties = [p for (p,) in parties_result.all() if p]
    out: list[PartyOut] = []
    for party in parties:
        cand_result = await db.execute(
            select(Candidate)
            .options(selectinload(Candidate.parliamentary_group))
            .where(Candidate.party == party)
            .order_by(Candidate.full_name)
        )
        candidates = list(cand_result.scalars().all())
        candidate_ids = [c.id for c in candidates]
        vote_count = 0
        vote_stats = VoteStatsOut()
        if candidate_ids:
            vote_count = await db.scalar(
                select(func.count())
                .select_from(ParliamentaryVote)
                .where(ParliamentaryVote.candidate_id.in_(candidate_ids))
            ) or 0
            vote_stats = await _vote_stats_for_filter(
                db, ParliamentaryVote.candidate_id.in_(candidate_ids)
            )
        out.append(
            PartyOut(
                party=party,
                candidate_count=len(candidates),
                vote_count=vote_count,
                vote_stats=vote_stats,
                candidates=[CandidateOut.model_validate(c) for c in candidates],
            )
        )
    return out


@router.get("/parties/{party}", response_model=PartyOut)
async def get_party(party: str, db: AsyncSession = Depends(get_db)) -> PartyOut:
    cand_result = await db.execute(
        select(Candidate)
        .options(selectinload(Candidate.parliamentary_group))
        .where(Candidate.party == party)
        .order_by(Candidate.full_name)
    )
    candidates = list(cand_result.scalars().all())
    if not candidates:
        raise HTTPException(status_code=404, detail="Parti introuvable")
    candidate_ids = [c.id for c in candidates]
    vote_count = await db.scalar(
        select(func.count())
        .select_from(ParliamentaryVote)
        .where(ParliamentaryVote.candidate_id.in_(candidate_ids))
    )
    return PartyOut(
        party=party,
        candidate_count=len(candidates),
        vote_count=vote_count or 0,
        vote_stats=await _vote_stats_for_filter(
            db, ParliamentaryVote.candidate_id.in_(candidate_ids)
        ),
        candidates=[CandidateOut.model_validate(c) for c in candidates],
    )


@router.get("/ingestion/runs", response_model=list[IngestionRunOut])
async def list_ingestion_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionRun]:
    result = await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


@router.post(
    "/ingestion/trigger",
    response_model=IngestionRunOut,
    dependencies=[Depends(require_ingestion_secret)],
)
async def trigger_ingestion(db: AsyncSession = Depends(get_db)) -> IngestionRun:
    from app.ingestion.orchestrator import IngestionOrchestrator

    orchestrator = IngestionOrchestrator(db)
    return await orchestrator.run()


async def _get_candidate_or_404(db: AsyncSession, slug: str) -> Candidate:
    result = await db.execute(select(Candidate).where(Candidate.slug == slug))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidat introuvable")
    return candidate


async def _vote_stats_for_filter(db: AsyncSession, *filters) -> VoteStatsOut:
    stmt = select(
        func.count().label("total"),
        func.coalesce(func.sum(case((ParliamentaryVote.position == "pour", 1), else_=0)), 0).label(
            "pour"
        ),
        func.coalesce(
            func.sum(case((ParliamentaryVote.position == "contre", 1), else_=0)), 0
        ).label("contre"),
        func.coalesce(
            func.sum(case((ParliamentaryVote.position == "abstention", 1), else_=0)), 0
        ).label("abstention"),
        func.coalesce(
            func.sum(
                case(
                    (
                        ParliamentaryVote.group_position.is_not(None),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("with_group"),
        func.coalesce(
            func.sum(
                case(
                    (
                        (ParliamentaryVote.group_position.is_not(None))
                        & (ParliamentaryVote.position == ParliamentaryVote.group_position),
                        1,
                    ),
                    else_=0,
                )
            ),
            0,
        ).label("aligned"),
    ).select_from(ParliamentaryVote)
    for f in filters:
        stmt = stmt.where(f)

    row = (await db.execute(stmt)).one()
    total = int(row.total or 0)
    pour = int(row.pour or 0)
    contre = int(row.contre or 0)
    abstention = int(row.abstention or 0)
    with_group = int(row.with_group or 0)
    aligned = int(row.aligned or 0)
    other = max(total - pour - contre - abstention, 0)
    loyalty = round(aligned / with_group, 3) if with_group else None
    return VoteStatsOut(
        total=total,
        pour=pour,
        contre=contre,
        abstention=abstention,
        other=other,
        with_group_position=with_group,
        aligned_with_group=aligned,
        loyalty_rate=loyalty,
    )
