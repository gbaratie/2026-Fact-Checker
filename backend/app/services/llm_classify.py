"""Classification thèmes votes + extraction claims programmes via LLM."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Candidate, ParliamentaryVote, ProgramDocument, Topic
from app.schemas import ClaimCreate, VoteTopicSet
from app.services import claims as claims_service
from app.services.llm_client import LlmConfigError, LlmRequestError, chat_json

logger = logging.getLogger(__name__)

VALID_STANCES = frozenset({"pour", "contre", "nuance", "inconnu"})
MAX_TOPICS_PER_VOTE = 2
PROGRAM_EXCERPT_CHARS = 12_000


def _topics_prompt_block(topics: list[Topic]) -> str:
    lines = []
    for t in topics:
        desc = (t.description or "").strip()
        lines.append(f"- {t.slug}: {t.label}" + (f" — {desc}" if desc else ""))
    return "\n".join(lines)


def filter_topic_slugs(raw: object, allowed: set[str], *, max_topics: int = MAX_TOPICS_PER_VOTE) -> list[str]:
    """Normalise et filtre les slugs renvoyés par le LLM."""
    if not isinstance(raw, list):
        return []
    seen: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        slug = item.strip()
        if slug in allowed and slug not in seen:
            seen.append(slug)
        if len(seen) >= max_topics:
            break
    return seen


def clamp_confidence(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def parse_vote_classification(data: dict, allowed: set[str]) -> tuple[list[str], float | None]:
    slugs = filter_topic_slugs(data.get("topic_slugs"), allowed)
    confidence = clamp_confidence(data.get("confidence"))
    return slugs, confidence


def parse_program_claims(data: dict, allowed: set[str]) -> list[dict]:
    raw_claims = data.get("claims")
    if not isinstance(raw_claims, list):
        return []

    parsed: list[dict] = []
    for item in raw_claims:
        if not isinstance(item, dict):
            continue
        topic_slug = item.get("topic_slug")
        stance = item.get("stance")
        summary = item.get("summary")
        if not isinstance(topic_slug, str) or topic_slug.strip() not in allowed:
            continue
        if not isinstance(stance, str) or stance.strip() not in VALID_STANCES:
            continue
        if not isinstance(summary, str) or len(summary.strip()) < 3:
            continue
        quote = item.get("quote")
        quote_clean = quote.strip() if isinstance(quote, str) and quote.strip() else None
        parsed.append(
            {
                "topic_slug": topic_slug.strip(),
                "stance": stance.strip(),
                "summary": summary.strip()[:500],
                "quote": quote_clean[:1000] if quote_clean else None,
                "confidence": clamp_confidence(item.get("confidence")),
            }
        )
    return parsed


async def classify_vote_topics(
    session: AsyncSession,
    candidate: Candidate,
    *,
    only_untagged: bool = True,
    limit: int = 30,
) -> dict:
    topics = await claims_service.list_topics(session)
    if not topics:
        raise LookupError("Aucun thème en base — lance POST /admin/seed-topics")

    allowed = {t.slug for t in topics}
    topics_block = _topics_prompt_block(topics)

    stmt = (
        select(ParliamentaryVote)
        .options(selectinload(ParliamentaryVote.vote_topics))
        .where(ParliamentaryVote.candidate_id == candidate.id)
        .order_by(ParliamentaryVote.vote_date.desc().nullslast())
    )
    result = await session.execute(stmt)
    votes = list(result.scalars().all())

    if only_untagged:
        votes = [v for v in votes if not v.vote_topics]

    votes = votes[: max(1, min(limit, 100))]

    classified = 0
    skipped = 0
    errors: list[str] = []

    system = (
        "Tu classifies des scrutins parlementaires français dans une taxonomie fixe. "
        "Réponds uniquement en JSON : "
        '{"topic_slugs": ["slug", ...], "confidence": 0.0-1.0}. '
        f"Choisis 0 à {MAX_TOPICS_PER_VOTE} thèmes parmi la liste fournie. "
        "Si le titre est trop technique ou hors sujet, renvoie une liste vide."
    )

    for vote in votes:
        user = (
            f"Thèmes autorisés:\n{topics_block}\n\n"
            f"Titre du scrutin:\n{vote.title}\n\n"
            "Retourne topic_slugs (slugs uniquement) et confidence."
        )
        try:
            data = await chat_json(system=system, user=user)
            slugs, _confidence = parse_vote_classification(data, allowed)
            if not slugs:
                skipped += 1
                continue
            await claims_service.set_vote_topics(session, vote, VoteTopicSet(topic_slugs=slugs))
            classified += 1
        except (LlmConfigError, LlmRequestError) as e:
            errors.append(f"vote {vote.id}: {e}")
            if isinstance(e, LlmConfigError):
                break
        except Exception as e:
            logger.exception("classify vote %s failed", vote.id)
            errors.append(f"vote {vote.id}: {e}")

    return {
        "classified": classified,
        "skipped": skipped,
        "processed": classified + skipped + len(errors),
        "errors": errors,
    }


async def extract_program_claims(
    session: AsyncSession,
    candidate: Candidate,
    *,
    limit_programs: int = 5,
    max_claims_per_program: int = 8,
) -> dict:
    topics = await claims_service.list_topics(session)
    if not topics:
        raise LookupError("Aucun thème en base — lance POST /admin/seed-topics")

    allowed = {t.slug for t in topics}
    topics_block = _topics_prompt_block(topics)

    result = await session.execute(
        select(ProgramDocument)
        .where(ProgramDocument.candidate_id == candidate.id)
        .order_by(ProgramDocument.year.desc().nullslast())
    )
    programs = [
        p
        for p in result.scalars().all()
        if p.excerpt and p.excerpt.strip()
    ][: max(1, min(limit_programs, 20))]

    existing = await claims_service.list_claims_for_candidate(session, candidate.id)
    existing_keys = {(c.topic.slug, c.summary.strip().lower()) for c in existing if c.topic}

    created = 0
    skipped = 0
    errors: list[str] = []

    system = (
        "Tu extrais des positions politiques structurées depuis un extrait de programme. "
        "Réponds uniquement en JSON : "
        '{"claims": [{"topic_slug": "...", "stance": "pour|contre|nuance|inconnu", '
        '"summary": "...", "quote": "...", "confidence": 0.0-1.0}]}. '
        f"Maximum {max_claims_per_program} claims. "
        "Utilise uniquement les topic_slug de la liste. "
        "summary = phrase courte en français (pas de liste). "
        "quote = citation courte du texte si possible, sinon null."
    )

    for program in programs:
        excerpt = program.excerpt.strip()[:PROGRAM_EXCERPT_CHARS]
        user = (
            f"Candidat: {candidate.full_name}\n"
            f"Document: {program.title}\n"
            f"Thèmes autorisés:\n{topics_block}\n\n"
            f"Extrait:\n{excerpt}"
        )
        try:
            data = await chat_json(system=system, user=user)
            parsed = parse_program_claims(data, allowed)[:max_claims_per_program]
            if not parsed:
                skipped += 1
                continue
            for item in parsed:
                key = (item["topic_slug"], item["summary"].lower())
                if key in existing_keys:
                    skipped += 1
                    continue
                payload = ClaimCreate(
                    topic_slug=item["topic_slug"],
                    stance=item["stance"],
                    summary=item["summary"],
                    quote=item["quote"],
                    evidence_type="program",
                    program_document_id=program.id,
                    source_url=program.url,
                    method="llm",
                    confidence=item["confidence"],
                )
                await claims_service.create_claim(session, candidate, payload)
                existing_keys.add(key)
                created += 1
        except (LlmConfigError, LlmRequestError) as e:
            errors.append(f"program {program.id}: {e}")
            if isinstance(e, LlmConfigError):
                break
        except Exception as e:
            logger.exception("extract claims from program %s failed", program.id)
            errors.append(f"program {program.id}: {e}")

    return {
        "created": created,
        "skipped": skipped,
        "programs_processed": len(programs),
        "errors": errors,
    }
