"""Ingestion ciblée des votes Assemblée (CLAIR.vote), sans YouTube ni presse."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import async_session_factory
from app.ingestion.orchestrator import IngestionOrchestrator
from app.models import Candidate, IngestionRun

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    async with async_session_factory() as session:
        orchestrator = IngestionOrchestrator(session)
        run = IngestionRun(status="running", stats={"votes": 0, "errors": 0})
        session.add(run)
        await session.flush()

        stats = {"votes": 0, "errors": 0, "matched": 0, "skipped": 0}
        errors: list[str] = []

        result = await session.execute(select(Candidate))
        candidates = result.scalars().all()

        for candidate in candidates:
            try:
                added = await orchestrator._ingest_votes(candidate, run)
                stats["votes"] += added
                ids = candidate.external_ids or {}
                if added or ids.get("clair_slug") or ids.get("clair_senateur_slug"):
                    stats["matched"] += 1
                    logger.info(
                        "%s: +%d votes (an=%s, senat=%s)",
                        candidate.slug,
                        added,
                        ids.get("clair_slug"),
                        ids.get("clair_senateur_slug"),
                    )
                else:
                    stats["skipped"] += 1
                    logger.info("%s: no AN/Senate match, skipped", candidate.slug)
                # Laisse respirer l'API CLAIR entre candidats.
                await asyncio.sleep(1.0)
            except Exception as e:
                msg = f"{candidate.slug}: {e}"
                logger.exception(msg)
                errors.append(msg)
                stats["errors"] += 1

        run.status = "completed" if not errors else "completed_with_errors"
        run.finished_at = datetime.now(UTC)
        run.stats = stats
        run.errors = errors
        await session.commit()
        logger.info("Votes ingestion %s finished: %s", run.id, stats)


if __name__ == "__main__":
    asyncio.run(main())
