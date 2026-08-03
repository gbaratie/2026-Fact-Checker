import asyncio
import logging
from pathlib import Path

import yaml
from sqlalchemy import select

from app.connectors.parliament import ParliamentConnector
from app.db.session import async_session_factory
from app.models import Candidate, ProgramDocument, Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEEDS_PATH = Path(__file__).resolve().parents[2] / "seeds" / "candidates.yaml"


async def seed_candidates() -> None:
    with SEEDS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    parliament = ParliamentConnector()

    async with async_session_factory() as session:
        for entry in data.get("candidates", []):
            result = await session.execute(
                select(Candidate).where(Candidate.slug == entry["slug"])
            )
            candidate = result.scalar_one_or_none()

            external_ids = entry.get("external_ids") or {}
            if not external_ids.get("depute_id"):
                depute = await parliament.search_depute(entry["full_name"])
                if depute:
                    depute_id = str(depute.get("id") or depute.get("uid") or "")
                    if depute_id:
                        external_ids["depute_id"] = depute_id
                        logger.info("Matched %s -> depute_id %s", entry["slug"], depute_id)

            if candidate:
                candidate.full_name = entry["full_name"]
                candidate.party = entry.get("party")
                candidate.status = entry.get("status", "potential")
                candidate.external_ids = external_ids
                logger.info("Updated candidate %s", entry["slug"])
            else:
                candidate = Candidate(
                    slug=entry["slug"],
                    full_name=entry["full_name"],
                    party=entry.get("party"),
                    status=entry.get("status", "potential"),
                    external_ids=external_ids,
                )
                session.add(candidate)
                await session.flush()
                logger.info("Created candidate %s", entry["slug"])

            await _seed_programs(session, candidate, entry.get("programs") or [])

        await session.commit()


async def _seed_programs(session, candidate: Candidate, programs: list[dict]) -> None:
    for prog in programs:
        url = prog["url"]
        existing = await session.execute(
            select(ProgramDocument).where(
                ProgramDocument.candidate_id == candidate.id,
                ProgramDocument.url == url,
            )
        )
        document = existing.scalar_one_or_none()

        source = Source(
            source_type="program",
            url=url,
            publisher=prog.get("publisher"),
            raw_metadata={
                "retrieved_via": "curated_seed",
                "source_url": url,
                "kind": prog.get("kind"),
                "year": prog.get("year"),
                "note": prog.get("note"),
            },
        )
        session.add(source)
        await session.flush()

        if document:
            document.title = prog["title"]
            document.kind = prog["kind"]
            document.year = prog.get("year")
            document.publisher = prog.get("publisher")
            document.note = prog.get("note")
            document.source_id = source.id
            logger.info("Updated program %s for %s", url, candidate.slug)
        else:
            session.add(
                ProgramDocument(
                    candidate_id=candidate.id,
                    source_id=source.id,
                    title=prog["title"],
                    url=url,
                    kind=prog["kind"],
                    year=prog.get("year"),
                    publisher=prog.get("publisher"),
                    note=prog.get("note"),
                )
            )
            logger.info("Created program %s for %s", url, candidate.slug)


async def main() -> None:
    await seed_candidates()


if __name__ == "__main__":
    asyncio.run(main())
