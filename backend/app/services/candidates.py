"""Création / suppression de candidats et import du seed YAML."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.connectors.parliament import ParliamentConnector
from app.models import (
    Article,
    Candidate,
    Interview,
    ParliamentaryVote,
    ProgramDocument,
    Source,
)
from app.schemas import CandidateCreate
from app.seeds.seed_candidates import seed_candidates
from app.utils.text import slugify


async def create_candidate(session: AsyncSession, payload: CandidateCreate) -> Candidate:
    slug = payload.slug or slugify(payload.full_name)
    if not slug:
        raise ValueError("Impossible de dériver un slug depuis le nom")

    existing = await session.execute(select(Candidate).where(Candidate.slug == slug))
    if existing.scalar_one_or_none():
        raise LookupError(f"Un candidat avec le slug « {slug} » existe déjà")

    external_ids: dict = {}
    if payload.clair_slug:
        external_ids["clair_slug"] = payload.clair_slug

    parliament = ParliamentConnector()
    depute = await parliament.resolve_depute(
        payload.full_name,
        preferred_slug=payload.clair_slug or slug,
    )
    if depute:
        external_ids["clair_slug"] = depute.slug
        external_ids["clair_id"] = depute.id
        external_ids["depute_id"] = depute.id

    candidate = Candidate(
        slug=slug,
        full_name=payload.full_name,
        party=payload.party,
        status=payload.status,
        external_ids=external_ids,
    )
    session.add(candidate)
    await session.commit()

    result = await session.execute(
        select(Candidate)
        .options(selectinload(Candidate.parliamentary_group))
        .where(Candidate.id == candidate.id)
    )
    return result.scalar_one()


async def delete_candidate(session: AsyncSession, slug: str) -> None:
    result = await session.execute(select(Candidate).where(Candidate.slug == slug))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise LookupError("Candidat introuvable")

    source_ids: set = set()
    for model in (Interview, ParliamentaryVote, Article, ProgramDocument):
        rows = await session.execute(
            select(model.source_id).where(model.candidate_id == candidate.id)
        )
        source_ids.update(rows.scalars().all())
        await session.execute(delete(model).where(model.candidate_id == candidate.id))

    if source_ids:
        await session.execute(delete(Source).where(Source.id.in_(source_ids)))

    await session.delete(candidate)
    await session.commit()


async def import_seed_candidates() -> dict[str, int]:
    """Importe/maj les candidats du YAML seed (idempotent)."""
    return await seed_candidates()
