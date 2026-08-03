import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.parliament import ParliamentConnector
from app.connectors.press_rss import PressRSSConnector
from app.connectors.programs import ProgramsConnector
from app.connectors.youtube import YouTubeConnector
from app.models import (
    Article,
    Candidate,
    IngestionRun,
    Interview,
    ParliamentaryGroup,
    ParliamentaryVote,
    ProgramDocument,
    Source,
)

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parliament = ParliamentConnector()
        self.youtube = YouTubeConnector()
        self.press = PressRSSConnector()
        self.programs = ProgramsConnector()

    async def run(self) -> IngestionRun:
        run = IngestionRun(status="running", stats={"created": 0, "updated": 0, "errors": 0})
        self.session.add(run)
        await self.session.flush()

        stats = {"interviews": 0, "votes": 0, "articles": 0, "programs": 0, "errors": 0}
        errors: list[str] = []

        result = await self.session.execute(select(Candidate))
        candidates = result.scalars().all()

        for candidate in candidates:
            try:
                stats["interviews"] += await self._ingest_interviews(candidate, run)
                stats["votes"] += await self._ingest_votes(candidate, run)
                stats["articles"] += await self._ingest_articles(candidate, run)
                stats["programs"] += await self._ingest_programs(candidate, run)
            except Exception as e:
                msg = f"{candidate.slug}: {e}"
                logger.exception(msg)
                errors.append(msg)
                stats["errors"] += 1

        run.status = "completed" if not errors else "completed_with_errors"
        run.finished_at = datetime.now(UTC)
        run.stats = stats
        run.errors = errors
        await self.session.commit()
        return run

    async def _ingest_interviews(self, candidate: Candidate, run: IngestionRun) -> int:
        records = await self.youtube.search_interviews(candidate.full_name)
        count = 0
        for record in records:
            existing = await self.session.execute(
                select(Interview).where(Interview.youtube_video_id == record.youtube_video_id)
            )
            interview = existing.scalar_one_or_none()

            source = Source(
                source_type="youtube",
                url=record.source_url,
                publisher=record.channel_name,
                raw_metadata=record.raw_metadata,
                ingestion_run_id=run.id,
            )
            self.session.add(source)
            await self.session.flush()

            if interview:
                interview.title = record.title
                interview.channel_name = record.channel_name
                interview.transcript = record.transcript or interview.transcript
                interview.published_at = record.published_at
                interview.source_id = source.id
            else:
                interview = Interview(
                    candidate_id=candidate.id,
                    source_id=source.id,
                    youtube_video_id=record.youtube_video_id,
                    title=record.title,
                    channel_name=record.channel_name,
                    transcript=record.transcript,
                    published_at=record.published_at,
                )
                self.session.add(interview)
                count += 1

        await self.session.flush()
        return count

    async def _ingest_votes(self, candidate: Candidate, run: IngestionRun) -> int:
        external_ids = dict(candidate.external_ids or {})
        clair_slug = external_ids.get("clair_slug")
        group = None

        depute = await self.parliament.resolve_depute(
            candidate.full_name, preferred_slug=clair_slug or candidate.slug
        )
        if depute:
            clair_slug = depute.slug
            external_ids["clair_slug"] = depute.slug
            external_ids["clair_id"] = depute.id
            external_ids["depute_id"] = depute.id
            candidate.external_ids = external_ids
            if depute.group:
                group = await self._upsert_group(depute.group)
                candidate.parliamentary_group_id = group.id
            await self.session.flush()

        if not clair_slug:
            logger.info("No CLAIR deputy match for %s, skipping votes", candidate.slug)
            return 0

        records = await self.parliament.fetch_votes_for_depute(clair_slug)
        count = 0
        for record in records:
            existing = await self.session.execute(
                select(ParliamentaryVote).where(
                    ParliamentaryVote.candidate_id == candidate.id,
                    ParliamentaryVote.scrutin_id == record.scrutin_id,
                )
            )
            vote = existing.scalar_one_or_none()

            source = Source(
                source_type="parliament",
                url=record.source_url,
                publisher=record.chamber,
                raw_metadata=record.raw_metadata,
                ingestion_run_id=run.id,
            )
            self.session.add(source)
            await self.session.flush()

            if vote:
                vote.title = record.title
                vote.position = record.position
                vote.group_position = record.group_position
                vote.vote_date = record.vote_date
                vote.source_id = source.id
                if group:
                    vote.parliamentary_group_id = group.id
            else:
                vote = ParliamentaryVote(
                    candidate_id=candidate.id,
                    source_id=source.id,
                    parliamentary_group_id=group.id if group else None,
                    chamber=record.chamber,
                    scrutin_id=record.scrutin_id,
                    title=record.title,
                    position=record.position,
                    group_position=record.group_position,
                    vote_date=record.vote_date,
                )
                self.session.add(vote)
                count += 1

        await self.session.flush()
        return count

    async def _upsert_group(self, info) -> ParliamentaryGroup:
        result = await self.session.execute(
            select(ParliamentaryGroup).where(ParliamentaryGroup.clair_id == info.clair_id)
        )
        group = result.scalar_one_or_none()
        if group:
            group.slug = info.slug
            group.name = info.name
            group.full_name = info.full_name
            group.color = info.color
            group.chamber = info.chamber
            group.legislature = info.legislature
            group.spectrum = info.spectrum
            group.raw_metadata = info.raw
            return group

        group = ParliamentaryGroup(
            clair_id=info.clair_id,
            slug=info.slug,
            name=info.name,
            full_name=info.full_name,
            color=info.color,
            chamber=info.chamber,
            legislature=info.legislature,
            spectrum=info.spectrum,
            raw_metadata=info.raw,
        )
        self.session.add(group)
        await self.session.flush()
        return group

    async def _ingest_articles(self, candidate: Candidate, run: IngestionRun) -> int:
        records = await self.press.fetch_articles_for_candidate(candidate.full_name)
        count = 0
        for record in records:
            existing = await self.session.execute(
                select(Article).where(Article.url == record.url)
            )
            article = existing.scalar_one_or_none()

            source = Source(
                source_type="press",
                url=record.url,
                publisher=record.publisher,
                raw_metadata=record.raw_metadata,
                ingestion_run_id=run.id,
            )
            self.session.add(source)
            await self.session.flush()

            if article:
                article.title = record.title
                article.excerpt = record.excerpt
                article.published_at = record.published_at
                article.source_id = source.id
            else:
                article = Article(
                    candidate_id=candidate.id,
                    source_id=source.id,
                    title=record.title,
                    url=record.url,
                    publisher=record.publisher,
                    excerpt=record.excerpt,
                    published_at=record.published_at,
                )
                self.session.add(article)
                count += 1

        await self.session.flush()
        return count

    async def _ingest_programs(self, candidate: Candidate, run: IngestionRun) -> int:
        records = await self.programs.fetch_programs_for_candidate(candidate.slug)
        count = 0
        for record in records:
            existing = await self.session.execute(
                select(ProgramDocument).where(
                    ProgramDocument.candidate_id == candidate.id,
                    ProgramDocument.url == record.url,
                )
            )
            document = existing.scalar_one_or_none()

            source = Source(
                source_type="program",
                url=record.url,
                publisher=record.publisher,
                raw_metadata=record.raw_metadata,
                ingestion_run_id=run.id,
            )
            self.session.add(source)
            await self.session.flush()

            if document:
                document.title = record.title
                document.kind = record.kind
                document.year = record.year
                document.publisher = record.publisher
                document.excerpt = record.excerpt or document.excerpt
                document.note = record.note
                document.source_id = source.id
            else:
                self.session.add(
                    ProgramDocument(
                        candidate_id=candidate.id,
                        source_id=source.id,
                        title=record.title,
                        url=record.url,
                        kind=record.kind,
                        year=record.year,
                        publisher=record.publisher,
                        excerpt=record.excerpt,
                        note=record.note,
                    )
                )
                count += 1

        await self.session.flush()
        return count
