import asyncio
import logging

from app.db.session import async_session_factory
from app.ingestion.orchestrator import IngestionOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    async with async_session_factory() as session:
        orchestrator = IngestionOrchestrator(session)
        run = await orchestrator.run()
        logger.info("Ingestion %s finished: %s", run.id, run.stats)


if __name__ == "__main__":
    asyncio.run(main())
