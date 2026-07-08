import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from dateutil import parser as date_parser
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class InterviewRecord:
    youtube_video_id: str
    title: str
    channel_name: str | None
    transcript: str | None
    published_at: datetime | None
    source_url: str
    raw_metadata: dict


class YouTubeConnector:
    def __init__(self) -> None:
        self.api_key = settings.youtube_api_key

    async def search_interviews(self, candidate_name: str, max_results: int = 10) -> list[InterviewRecord]:
        if not self.api_key:
            logger.warning("YOUTUBE_API_KEY not set, skipping YouTube ingestion")
            return []

        query = f'"{candidate_name}" interview présidentielle 2026'
        video_ids = await self._search_videos(query, max_results)
        if not video_ids:
            return []

        videos_meta = await self._fetch_video_details(video_ids)
        records: list[InterviewRecord] = []
        for video in videos_meta:
            video_id = video["id"]
            transcript = self._fetch_transcript(video_id)
            snippet = video.get("snippet", {})
            published_at = self._parse_date(snippet.get("publishedAt"))
            records.append(
                InterviewRecord(
                    youtube_video_id=video_id,
                    title=snippet.get("title", "Sans titre")[:500],
                    channel_name=snippet.get("channelTitle"),
                    transcript=transcript,
                    published_at=published_at,
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    raw_metadata={
                        "description": snippet.get("description", "")[:2000],
                        "channel_id": snippet.get("channelId"),
                        "statistics": video.get("statistics", {}),
                    },
                )
            )
        return records

    async def _search_videos(self, query: str, max_results: int) -> list[str]:
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "medium",
            "relevanceLanguage": "fr",
            "maxResults": max_results,
            "key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(YOUTUBE_SEARCH_URL, params=params)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [
                item["id"]["videoId"]
                for item in items
                if item.get("id", {}).get("videoId")
            ]

    async def _fetch_video_details(self, video_ids: list[str]) -> list[dict]:
        if not video_ids:
            return []
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(YOUTUBE_VIDEOS_URL, params=params)
            resp.raise_for_status()
            return resp.json().get("items", [])

    def _fetch_transcript(self, video_id: str) -> str | None:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for lang in ("fr", "fr-FR"):
                try:
                    transcript = transcript_list.find_transcript([lang])
                    segments = transcript.fetch()
                    return " ".join(seg["text"] for seg in segments)
                except NoTranscriptFound:
                    continue
            try:
                transcript = transcript_list.find_generated_transcript(["fr"])
                segments = transcript.fetch()
                return " ".join(seg["text"] for seg in segments)
            except NoTranscriptFound:
                return None
        except (TranscriptsDisabled, VideoUnavailable, Exception) as e:
            logger.debug("No transcript for %s: %s", video_id, e)
            return None

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return date_parser.parse(value)
        except (ValueError, TypeError):
            return None
