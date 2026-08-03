import logging
from dataclasses import dataclass
from datetime import datetime
from time import struct_time
from urllib.parse import urlparse

import feedparser
import httpx
import trafilatura

from app.config import settings
from app.utils.text import candidate_mentioned

logger = logging.getLogger(__name__)

USER_AGENT = "FactChecker2026/0.1 (+https://github.com/fact-checker)"

PUBLISHER_BY_DOMAIN: dict[str, str] = {
    "www.lemonde.fr": "Le Monde",
    "www.franceinfo.fr": "franceinfo",
    "www.francetvinfo.fr": "franceinfo",
    "www.lefigaro.fr": "Le Figaro",
    "www.liberation.fr": "Libération",
    "www.lexpress.fr": "L'Express",
    "www.nouvelobs.com": "Le Nouvel Obs",
    "www.leparisien.fr": "Le Parisien",
    "feeds.leparisien.fr": "Le Parisien",
    "www.20minutes.fr": "20 Minutes",
    "www.bfmtv.com": "BFMTV",
    "www.france24.com": "France 24",
    "www.publicsenat.fr": "Public Sénat",
    "www.mediapart.fr": "Mediapart",
    "www.politico.eu": "POLITICO",
    "www.huffingtonpost.fr": "HuffPost",
    "www.challenges.fr": "Challenges",
    "www.slate.fr": "Slate",
    "www.humanite.fr": "L'Humanité",
    "www.la-croix.com": "La Croix",
    "www.sudouest.fr": "Sud Ouest",
}


@dataclass
class ArticleRecord:
    title: str
    url: str
    publisher: str | None
    excerpt: str | None
    published_at: datetime | None
    raw_metadata: dict


class PressRSSConnector:
    def __init__(self) -> None:
        self.feeds = settings.rss_feeds

    async def fetch_articles_for_candidate(
        self, candidate_name: str, max_per_feed: int = 20
    ) -> list[ArticleRecord]:
        records: list[ArticleRecord] = []
        seen_urls: set[str] = set()

        for feed_url in self.feeds:
            try:
                feed = await self._parse_feed(feed_url)
                publisher = self._publisher_for_feed(feed_url, feed)
                feed_title = feed.feed.get("title") or publisher
                count = 0
                for entry in feed.entries:
                    if count >= max_per_feed:
                        break
                    title = entry.get("title", "")
                    url = entry.get("link", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    if not url or url in seen_urls:
                        continue
                    if not candidate_mentioned(f"{title} {summary}", candidate_name):
                        continue

                    published_at = self._parse_entry_date(entry.get("published_parsed"))
                    excerpt = await self._extract_excerpt(url, summary)
                    records.append(
                        ArticleRecord(
                            title=title[:500],
                            url=url,
                            publisher=publisher,
                            excerpt=excerpt,
                            published_at=published_at,
                            raw_metadata={
                                "retrieved_via": "rss",
                                "feed_url": feed_url,
                                "feed_title": feed_title,
                                "publisher": publisher,
                            },
                        )
                    )
                    seen_urls.add(url)
                    count += 1
            except Exception as e:
                logger.warning("RSS feed %s failed: %s", feed_url, e)

        return records

    async def _parse_feed(self, feed_url: str):
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(feed_url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return feedparser.parse(resp.text)

    @staticmethod
    def _publisher_for_feed(feed_url: str, feed) -> str:
        domain = urlparse(feed_url).netloc.lower()
        if domain in PUBLISHER_BY_DOMAIN:
            return PUBLISHER_BY_DOMAIN[domain]
        return feed.feed.get("title") or domain

    async def _extract_excerpt(self, url: str, fallback: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                text = trafilatura.extract(resp.text, include_comments=False)
                if text:
                    return text[:500]
        except Exception as e:
            logger.debug("trafilatura failed for %s: %s", url, e)

        if fallback:
            import re

            clean = re.sub(r"<[^>]+>", "", fallback)
            return clean[:500]
        return None

    @staticmethod
    def _parse_entry_date(parsed: struct_time | None) -> datetime | None:
        if not parsed:
            return None
        try:
            return datetime(*parsed[:6])
        except (ValueError, TypeError):
            return None
