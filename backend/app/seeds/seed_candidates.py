import asyncio
import logging
from pathlib import Path

import yaml
from sqlalchemy import select

from app.connectors.parliament import ParliamentConnector
from app.db.session import async_session_factory
from app.models import Candidate

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

            external_ids = dict(entry.get("external_ids") or {})
            if not external_ids.get("clair_slug"):
                depute = await parliament.resolve_depute(
                    entry["full_name"], preferred_slug=entry["slug"]
                )
                if depute:
                    external_ids["clair_slug"] = depute.slug
                    external_ids["clair_id"] = depute.id
                    external_ids["depute_id"] = depute.id
                    logger.info(
                        "Matched %s -> clair_slug %s (actif=%s)",
                        entry["slug"],
                        depute.slug,
                        depute.actif,
                    )
                else:
                    logger.info("No Assemblee match for %s", entry["slug"])

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
                logger.info("Created candidate %s", entry["slug"])

        await session.commit()


async def main() -> None:
    await seed_candidates()


if __name__ == "__main__":
    asyncio.run(main())
