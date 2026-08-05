"""CRUD claims, tagging votes↔thèmes, agrégats de cohérence."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Article,
    Candidate,
    Claim,
    Interview,
    ParliamentaryVote,
    ProgramDocument,
    Topic,
    VoteTopic,
)
from app.schemas import ClaimCreate, ClaimUpdate, VoteTopicSet
from app.services.coherence import topic_coherence_status


async def list_topics(session: AsyncSession) -> list[Topic]:
    result = await session.execute(select(Topic).order_by(Topic.sort_order, Topic.label))
    return list(result.scalars().all())


async def get_topic_by_slug(session: AsyncSession, slug: str) -> Topic | None:
    result = await session.execute(select(Topic).where(Topic.slug == slug))
    return result.scalar_one_or_none()


async def list_claims_for_candidate(session: AsyncSession, candidate_id: UUID) -> list[Claim]:
    result = await session.execute(
        select(Claim)
        .options(selectinload(Claim.topic))
        .where(Claim.candidate_id == candidate_id)
        .order_by(Claim.created_at.desc())
    )
    return list(result.scalars().all())


async def _validate_evidence(
    session: AsyncSession,
    candidate_id: UUID,
    *,
    evidence_type: str,
    interview_id: UUID | None,
    program_document_id: UUID | None,
    article_id: UUID | None,
) -> None:
    if evidence_type == "interview":
        if not interview_id:
            raise ValueError("interview_id requis pour evidence_type=interview")
        row = await session.execute(
            select(Interview).where(
                Interview.id == interview_id, Interview.candidate_id == candidate_id
            )
        )
        if not row.scalar_one_or_none():
            raise ValueError("Interview introuvable pour ce candidat")
    elif evidence_type == "program":
        if not program_document_id:
            raise ValueError("program_document_id requis pour evidence_type=program")
        row = await session.execute(
            select(ProgramDocument).where(
                ProgramDocument.id == program_document_id,
                ProgramDocument.candidate_id == candidate_id,
            )
        )
        if not row.scalar_one_or_none():
            raise ValueError("Document de programme introuvable pour ce candidat")
    elif evidence_type == "article":
        if not article_id:
            raise ValueError("article_id requis pour evidence_type=article")
        row = await session.execute(
            select(Article).where(Article.id == article_id, Article.candidate_id == candidate_id)
        )
        if not row.scalar_one_or_none():
            raise ValueError("Article introuvable pour ce candidat")


async def create_claim(
    session: AsyncSession, candidate: Candidate, payload: ClaimCreate
) -> Claim:
    topic = await get_topic_by_slug(session, payload.topic_slug)
    if not topic:
        raise LookupError(f"Thème « {payload.topic_slug} » introuvable")

    await _validate_evidence(
        session,
        candidate.id,
        evidence_type=payload.evidence_type,
        interview_id=payload.interview_id,
        program_document_id=payload.program_document_id,
        article_id=payload.article_id,
    )

    claim = Claim(
        candidate_id=candidate.id,
        topic_id=topic.id,
        stance=payload.stance,
        summary=payload.summary,
        quote=payload.quote,
        evidence_type=payload.evidence_type,
        interview_id=payload.interview_id,
        program_document_id=payload.program_document_id,
        article_id=payload.article_id,
        source_url=payload.source_url,
        method=payload.method,
        confidence=payload.confidence,
    )
    session.add(claim)
    await session.commit()

    result = await session.execute(
        select(Claim).options(selectinload(Claim.topic)).where(Claim.id == claim.id)
    )
    return result.scalar_one()


async def update_claim(session: AsyncSession, claim_id: UUID, payload: ClaimUpdate) -> Claim:
    result = await session.execute(
        select(Claim).options(selectinload(Claim.topic)).where(Claim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise LookupError("Position introuvable")

    data = payload.model_dump(exclude_unset=True)

    if "topic_slug" in data:
        topic_slug = data.pop("topic_slug")
        if topic_slug is not None:
            topic = await get_topic_by_slug(session, topic_slug)
            if not topic:
                raise LookupError(f"Thème « {topic_slug} » introuvable")
            claim.topic_id = topic.id

    evidence_type = data.get("evidence_type", claim.evidence_type)
    interview_id = data.get("interview_id", claim.interview_id)
    program_document_id = data.get("program_document_id", claim.program_document_id)
    article_id = data.get("article_id", claim.article_id)

    if any(
        k in data
        for k in ("evidence_type", "interview_id", "program_document_id", "article_id")
    ):
        await _validate_evidence(
            session,
            claim.candidate_id,
            evidence_type=evidence_type,
            interview_id=interview_id,
            program_document_id=program_document_id,
            article_id=article_id,
        )

    for key, value in data.items():
        setattr(claim, key, value)

    claim.updated_at = datetime.now(UTC)
    await session.commit()

    result = await session.execute(
        select(Claim).options(selectinload(Claim.topic)).where(Claim.id == claim.id)
    )
    return result.scalar_one()


async def delete_claim(session: AsyncSession, claim_id: UUID) -> None:
    result = await session.execute(select(Claim).where(Claim.id == claim_id))
    claim = result.scalar_one_or_none()
    if not claim:
        raise LookupError("Position introuvable")
    await session.delete(claim)
    await session.commit()


async def set_vote_topics(
    session: AsyncSession, vote: ParliamentaryVote, payload: VoteTopicSet
) -> list[Topic]:
    topics: list[Topic] = []
    for slug in payload.topic_slugs:
        topic = await get_topic_by_slug(session, slug)
        if not topic:
            raise LookupError(f"Thème « {slug} » introuvable")
        topics.append(topic)

    await session.execute(delete(VoteTopic).where(VoteTopic.vote_id == vote.id))
    for topic in topics:
        session.add(VoteTopic(vote_id=vote.id, topic_id=topic.id))
    await session.commit()
    return topics


async def list_topics_for_vote(session: AsyncSession, vote_id: UUID) -> list[Topic]:
    result = await session.execute(
        select(Topic)
        .join(VoteTopic, VoteTopic.topic_id == Topic.id)
        .where(VoteTopic.vote_id == vote_id)
        .order_by(Topic.sort_order, Topic.label)
    )
    return list(result.scalars().all())


async def coherence_for_candidate(session: AsyncSession, candidate_id: UUID) -> list[dict]:
    topics = await list_topics(session)
    claims = await list_claims_for_candidate(session, candidate_id)

    vote_rows = await session.execute(
        select(ParliamentaryVote, Topic)
        .join(VoteTopic, VoteTopic.vote_id == ParliamentaryVote.id)
        .join(Topic, Topic.id == VoteTopic.topic_id)
        .where(ParliamentaryVote.candidate_id == candidate_id)
    )
    votes_by_topic: dict[UUID, list[ParliamentaryVote]] = {}
    for vote, topic in vote_rows.all():
        votes_by_topic.setdefault(topic.id, []).append(vote)

    claims_by_topic: dict[UUID, list[Claim]] = {}
    for claim in claims:
        claims_by_topic.setdefault(claim.topic_id, []).append(claim)

    rows: list[dict] = []
    for topic in topics:
        topic_claims = claims_by_topic.get(topic.id, [])
        topic_votes = votes_by_topic.get(topic.id, [])
        if not topic_claims and not topic_votes:
            continue
        status = topic_coherence_status(
            [c.stance for c in topic_claims],
            [v.position for v in topic_votes],
        )
        rows.append(
            {
                "topic": topic,
                "status": status,
                "claim_stances": sorted({c.stance for c in topic_claims}),
                "vote_positions": sorted({v.position for v in topic_votes}),
                "claims_count": len(topic_claims),
                "votes_count": len(topic_votes),
            }
        )
    return rows
