import io
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
import trafilatura
import yaml
from pypdf import PdfReader

logger = logging.getLogger(__name__)

USER_AGENT = "FactChecker2026/0.1 (+https://github.com/fact-checker)"
SEEDS_PATH = Path(__file__).resolve().parents[2] / "seeds" / "candidates.yaml"
EXCERPT_MAX = 1500


@dataclass
class ProgramRecord:
    title: str
    url: str
    kind: str
    year: int | None
    publisher: str | None
    excerpt: str | None
    note: str | None
    raw_metadata: dict


class ProgramsConnector:
    def __init__(self, seeds_path: Path | None = None) -> None:
        self.seeds_path = seeds_path or SEEDS_PATH
        self._by_slug: dict[str, list[dict]] | None = None

    def programs_for_slug(self, slug: str) -> list[dict]:
        if self._by_slug is None:
            with self.seeds_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._by_slug = {
                entry["slug"]: entry.get("programs") or []
                for entry in data.get("candidates", [])
            }
        return self._by_slug.get(slug, [])

    async def fetch_programs_for_candidate(self, slug: str) -> list[ProgramRecord]:
        records: list[ProgramRecord] = []
        for entry in self.programs_for_slug(slug):
            try:
                records.append(await self.fetch_program(entry))
            except Exception as e:
                logger.warning("Program fetch failed for %s (%s): %s", slug, entry.get("url"), e)
                records.append(
                    ProgramRecord(
                        title=entry["title"],
                        url=entry["url"],
                        kind=entry["kind"],
                        year=entry.get("year"),
                        publisher=entry.get("publisher"),
                        excerpt=None,
                        note=entry.get("note"),
                        raw_metadata={
                            "retrieved_via": "curated_seed",
                            "source_url": entry["url"],
                            "kind": entry["kind"],
                            "year": entry.get("year"),
                            "note": entry.get("note"),
                            "fetch_error": str(e),
                        },
                    )
                )
        return records

    async def fetch_program(self, entry: dict) -> ProgramRecord:
        url = entry["url"]
        excerpt, content_type = await self._extract_excerpt(url)
        return ProgramRecord(
            title=entry["title"],
            url=url,
            kind=entry["kind"],
            year=entry.get("year"),
            publisher=entry.get("publisher"),
            excerpt=excerpt,
            note=entry.get("note"),
            raw_metadata={
                "retrieved_via": "curated_seed",
                "source_url": url,
                "fetched_from": url,
                "kind": entry["kind"],
                "year": entry.get("year"),
                "note": entry.get("note"),
                "content_type": content_type,
            },
        )

    async def _extract_excerpt(self, url: str) -> tuple[str | None, str | None]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            data = resp.content

        if "pdf" in content_type or url.lower().endswith(".pdf"):
            return self._excerpt_from_pdf(data), content_type or "application/pdf"

        text = trafilatura.extract(data.decode("utf-8", errors="ignore"), include_comments=False)
        if text:
            return text[:EXCERPT_MAX], content_type or "text/html"
        return None, content_type

    @staticmethod
    def _excerpt_from_pdf(data: bytes) -> str | None:
        try:
            reader = PdfReader(io.BytesIO(data))
            chunks: list[str] = []
            for page in reader.pages[:5]:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(page_text.strip())
                if sum(len(c) for c in chunks) >= EXCERPT_MAX:
                    break
            text = "\n\n".join(chunks).strip()
            return text[:EXCERPT_MAX] if text else None
        except Exception as e:
            logger.debug("PDF extract failed: %s", e)
            return None
