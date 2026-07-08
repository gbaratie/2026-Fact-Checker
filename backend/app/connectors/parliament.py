import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from dateutil import parser as date_parser

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VoteRecord:
    chamber: str
    scrutin_id: str
    title: str
    position: str
    vote_date: datetime | None
    source_url: str
    raw_metadata: dict


class ParliamentConnector:
    def __init__(self) -> None:
        self.clair_base = settings.clair_api_base
        self.an_votes_url = settings.an_votes_url

    async def search_depute(self, name: str) -> dict | None:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(f"{self.clair_base}/deputes", params={"search": name})
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data") or data.get("items") or data
                if isinstance(items, list) and items:
                    return items[0]
                if isinstance(items, dict) and items.get("id"):
                    return items
            except Exception as e:
                logger.warning("CLAIR search failed for %s: %s", name, e)
        return None

    async def fetch_votes_for_depute(self, depute_id: str) -> list[VoteRecord]:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.get(f"{self.clair_base}/deputes/{depute_id}/votes")
                resp.raise_for_status()
                return self._parse_clair_votes(resp.json())
            except Exception as e:
                logger.warning("CLAIR votes failed for %s: %s", depute_id, e)

        return await self._fetch_an_fallback(client=None, depute_id=depute_id)

    def _parse_clair_votes(self, data: dict | list) -> list[VoteRecord]:
        records: list[VoteRecord] = []
        items = data
        if isinstance(data, dict):
            items = data.get("data") or data.get("votes") or data.get("items") or []

        if not isinstance(items, list):
            return records

        for item in items:
            scrutin = item.get("scrutin") or item
            scrutin_id = str(
                scrutin.get("id") or scrutin.get("uid") or item.get("scrutin_id") or ""
            )
            if not scrutin_id:
                continue

            title = (
                scrutin.get("titre")
                or scrutin.get("title")
                or item.get("titre")
                or "Scrutin sans titre"
            )
            position = (
                item.get("position")
                or item.get("vote")
                or item.get("choix")
                or "unknown"
            )
            vote_date = self._parse_date(
                scrutin.get("date") or item.get("date") or scrutin.get("dateScrutin")
            )
            chamber = scrutin.get("chambre") or item.get("chambre") or "assemblee"
            source_url = (
                scrutin.get("url")
                or f"https://clair.vote/scrutins/{scrutin_id}"
            )

            records.append(
                VoteRecord(
                    chamber=chamber,
                    scrutin_id=scrutin_id,
                    title=str(title)[:500],
                    position=str(position).lower(),
                    vote_date=vote_date,
                    source_url=source_url,
                    raw_metadata=item,
                )
            )
        return records

    async def _fetch_an_fallback(
        self, client: httpx.AsyncClient | None, depute_id: str
    ) -> list[VoteRecord]:
        records: list[VoteRecord] = []
        try:
            if client is None:
                async with httpx.AsyncClient(timeout=120) as c:
                    resp = await c.get(self.an_votes_url)
            else:
                resp = await client.get(self.an_votes_url)
            resp.raise_for_status()
            data = resp.json()
            scrutins = data.get("scrutins") or data
            if isinstance(scrutins, dict):
                scrutins = list(scrutins.values())

            for scrutin in scrutins if isinstance(scrutins, list) else []:
                scrutin_uid = str(scrutin.get("uid") or scrutin.get("numero") or "")
                titre = (
                    scrutin.get("titre", {}).get("titre")
                    if isinstance(scrutin.get("titre"), dict)
                    else scrutin.get("titre", "Scrutin")
                )
                vote_date = self._parse_date(scrutin.get("dateScrutin"))
                ventilation = scrutin.get("ventilationVotes", {})
                decompte = ventilation.get("decompte", {})
                for group_key, group_data in decompte.items():
                    votes = group_data.get("decompteNominatif", {})
                    for vote_type, vote_data in votes.items():
                        votants = vote_data.get("votants", {}).get("acteur", [])
                        if isinstance(votants, dict):
                            votants = [votants]
                        for acteur in votants:
                            acteur_id = str(acteur.get("acteurRef") or acteur.get("uid") or "")
                            if acteur_id and acteur_id == depute_id:
                                records.append(
                                    VoteRecord(
                                        chamber="assemblee",
                                        scrutin_id=scrutin_uid,
                                        title=str(titre)[:500],
                                        position=vote_type.lower(),
                                        vote_date=vote_date,
                                        source_url="https://data.assemblee-nationale.fr/travaux-parlementaires/votes",
                                        raw_metadata={"scrutin_uid": scrutin_uid, "group": group_key},
                                    )
                                )
        except Exception as e:
            logger.error("AN fallback failed: %s", e)
        return records

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return date_parser.parse(str(value))
        except (ValueError, TypeError):
            return None
