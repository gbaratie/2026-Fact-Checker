"""Import idempotent des thèmes depuis seeds/topics.yaml."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from sqlalchemy import select

from app.db.session import async_session_factory
from app.models import Topic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEEDS_PATH = Path(__file__).resolve().parents[2] / "seeds" / "topics.yaml"


async def seed_topics() -> dict[str, int]:
    with SEEDS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    created = 0
    updated = 0

    async with async_session_factory() as session:
        for entry in data.get("topics", []):
            result = await session.execute(select(Topic).where(Topic.slug == entry["slug"]))
            topic = result.scalar_one_or_none()
            if topic:
                topic.label = entry["label"]
                topic.description = entry.get("description")
                topic.sort_order = int(entry.get("sort_order", 0))
                updated += 1
                logger.info("Updated topic %s", entry["slug"])
            else:
                session.add(
                    Topic(
                        slug=entry["slug"],
                        label=entry["label"],
                        description=entry.get("description"),
                        sort_order=int(entry.get("sort_order", 0)),
                    )
                )
                created += 1
                logger.info("Created topic %s", entry["slug"])

        await session.commit()

    return {"created": created, "updated": updated, "total": created + updated}


async def main() -> None:
    await seed_topics()


if __name__ == "__main__":
    asyncio.run(main())
