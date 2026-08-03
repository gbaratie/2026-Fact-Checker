import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

import httpx
from dateutil import parser as date_parser

from app.config import settings
from app.utils.text import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class VoteRecord:
    chamber: str
    scrutin_id: str
    title: str
    position: str
    group_position: str | None
    vote_date: datetime | None
    source_url: str
    raw_metadata: dict


@dataclass
class GroupInfo:
    clair_id: str
    slug: str
    name: str
    full_name: str
    color: str | None
    chamber: str
    legislature: int | None
    spectrum: str | None
    raw: dict


@dataclass
class DeputeMatch:
    id: str
    slug: str
    full_name: str
    actif: bool
    group: GroupInfo | None
    raw: dict


class ParliamentConnector:
    """Connecteur CLAIR.vote pour les votes à l'Assemblée (et fallback AN)."""

    def __init__(self, page_size: int = 100, max_votes: int | None = 200) -> None:
        self.clair_base = settings.clair_api_base.rstrip("/")
        self.an_votes_url = settings.an_votes_url
        self.page_size = page_size
        # Première collecte : plafonner pour éviter des milliers d'appels.
        # None = tout récupérer.
        self.max_votes = max_votes
        self._request_delay_s = 0.5

    async def resolve_depute(
        self, full_name: str, preferred_slug: str | None = None
    ) -> DeputeMatch | None:
        """Résout un candidat vers un député CLAIR via slug exact, puis recherche stricte."""
        if preferred_slug:
            match = await self.get_depute_by_slug(preferred_slug)
            if match:
                return match

        return await self.search_depute(full_name)

    async def get_depute_by_slug(self, slug: str) -> DeputeMatch | None:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await self._clair_get(client, f"{self.clair_base}/deputes/{slug}")
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                data = resp.json().get("data") or resp.json()
                return self._to_match(data)
            except Exception as e:
                logger.warning("CLAIR get_depute_by_slug failed for %s: %s", slug, e)
        return None

    async def search_depute(self, name: str) -> DeputeMatch | None:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await self._clair_get(
                    client,
                    f"{self.clair_base}/deputes",
                    params={"search": name},
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data") or data.get("items") or data
                if not isinstance(items, list):
                    return None
                return self._best_name_match(name, items)
            except Exception as e:
                logger.warning("CLAIR search failed for %s: %s", name, e)
        return None

    async def fetch_votes_for_depute(self, depute_slug: str) -> list[VoteRecord]:
        """Récupère les votes via /deputes/{slug}/votes (CLAIR utilise le slug, pas l'UUID)."""
        records: list[VoteRecord] = []
        page_num = 1
        async with httpx.AsyncClient(timeout=60) as client:
            while True:
                try:
                    resp = await self._clair_get(
                        client,
                        f"{self.clair_base}/deputes/{depute_slug}/votes",
                        params={"limit": self.page_size, "page": page_num},
                    )
                    if resp.status_code == 404:
                        logger.warning("CLAIR votes not found for slug %s", depute_slug)
                        break
                    resp.raise_for_status()
                    payload = resp.json()
                    page = self._parse_clair_votes(payload)
                    if not page:
                        break
                    records.extend(page)

                    meta = payload.get("meta") if isinstance(payload, dict) else None
                    has_next = bool(meta and meta.get("hasNext"))
                    page_num += 1

                    if self.max_votes is not None and len(records) >= self.max_votes:
                        records = records[: self.max_votes]
                        break
                    if not has_next:
                        break
                except Exception as e:
                    logger.warning("CLAIR votes failed for %s: %s", depute_slug, e)
                    break

        if records:
            return records

        # Fallback open data AN (souvent fragile) — best effort.
        return await self._fetch_an_fallback(depute_slug)

    async def _clair_get(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict | None = None,
        max_retries: int = 5,
    ) -> httpx.Response:
        """GET CLAIR avec délai et retry sur 429."""
        await asyncio.sleep(self._request_delay_s)
        delay = 2.0
        last: httpx.Response | None = None
        for attempt in range(max_retries):
            last = await client.get(url, params=params)
            if last.status_code != 429:
                return last
            retry_after = last.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
            logger.info(
                "CLAIR rate-limited, retry in %.1fs (attempt %d/%d)",
                wait,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait)
            delay = min(delay * 2, 30)
        assert last is not None
        return last

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
                scrutin.get("numero")
                or scrutin.get("id")
                or scrutin.get("uid")
                or item.get("scrutin_id")
                or ""
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
            group_position_raw = item.get("groupePosition") or item.get("group_position")
            group_position = (
                str(group_position_raw).lower() if group_position_raw else None
            )
            vote_date = self._parse_date(
                scrutin.get("date") or item.get("date") or scrutin.get("dateScrutin")
            )
            chamber = scrutin.get("chambre") or item.get("chambre") or "assemblee"
            source_url = (
                scrutin.get("url")
                or f"https://clair.vote/scrutins/{scrutin.get('id') or scrutin_id}"
            )

            records.append(
                VoteRecord(
                    chamber=str(chamber),
                    scrutin_id=scrutin_id,
                    title=str(title)[:500],
                    position=str(position).lower(),
                    group_position=group_position,
                    vote_date=vote_date,
                    source_url=source_url,
                    raw_metadata=item,
                )
            )
        return records

    async def _fetch_an_fallback(self, depute_id: str) -> list[VoteRecord]:
        records: list[VoteRecord] = []
        try:
            async with httpx.AsyncClient(timeout=120) as client:
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
                    if not isinstance(group_data, dict):
                        continue
                    votes = group_data.get("decompteNominatif", {})
                    for vote_type, vote_data in votes.items():
                        if not isinstance(vote_data, dict):
                            continue
                        votants = vote_data.get("votants", {}).get("acteur", [])
                        if isinstance(votants, dict):
                            votants = [votants]
                        for acteur in votants:
                            acteur_id = str(
                                acteur.get("acteurRef") or acteur.get("uid") or ""
                            )
                            if acteur_id and acteur_id == depute_id:
                                records.append(
                                    VoteRecord(
                                        chamber="assemblee",
                                        scrutin_id=scrutin_uid,
                                        title=str(titre)[:500],
                                        position=vote_type.lower(),
                                        group_position=None,
                                        vote_date=vote_date,
                                        source_url=(
                                            "https://data.assemblee-nationale.fr/"
                                            "travaux-parlementaires/votes"
                                        ),
                                        raw_metadata={
                                            "scrutin_uid": scrutin_uid,
                                            "group": group_key,
                                        },
                                    )
                                )
        except Exception as e:
            logger.error("AN fallback failed: %s", e)
        return records

    def _best_name_match(self, full_name: str, items: list[dict]) -> DeputeMatch | None:
        """Évite les faux positifs CLAIR (ex: Macron → Emmanuel Mandon)."""
        target = normalize_text(full_name)
        if not target:
            return None

        exact: list[DeputeMatch] = []
        for item in items:
            match = self._to_match(item)
            if not match:
                continue
            if normalize_text(match.full_name) == target:
                exact.append(match)

        if exact:
            # Préférer un député actif en cas de doublons.
            exact.sort(key=lambda m: (not m.actif, m.slug))
            return exact[0]

        logger.info(
            "No exact CLAIR match for %r among %d results", full_name, len(items)
        )
        return None

    @classmethod
    def _to_match(cls, data: dict | None) -> DeputeMatch | None:
        if not isinstance(data, dict):
            return None
        slug = str(data.get("slug") or "").strip()
        depute_id = str(data.get("id") or data.get("uid") or "").strip()
        prenom = str(data.get("prenom") or "").strip()
        nom = str(data.get("nom") or "").strip()
        full_name = f"{prenom} {nom}".strip() or str(data.get("nomComplet") or "").strip()
        if not slug or not depute_id:
            return None
        return DeputeMatch(
            id=depute_id,
            slug=slug,
            full_name=full_name,
            actif=bool(data.get("actif", False)),
            group=cls._parse_group(data.get("groupe")),
            raw=data,
        )

    @staticmethod
    def _parse_group(data: dict | None) -> GroupInfo | None:
        if not isinstance(data, dict):
            return None
        clair_id = str(data.get("id") or "").strip()
        slug = str(data.get("slug") or "").strip()
        name = str(data.get("nom") or "").strip()
        full_name = str(data.get("nomComplet") or name).strip()
        if not clair_id or not slug or not name:
            return None
        legislature = data.get("legislature")
        return GroupInfo(
            clair_id=clair_id,
            slug=slug,
            name=name[:120],
            full_name=full_name[:255],
            color=(str(data["couleur"])[:20] if data.get("couleur") else None),
            chamber=str(data.get("chambre") or "assemblee"),
            legislature=int(legislature) if legislature is not None else None,
            spectrum=(str(data["position"])[:50] if data.get("position") else None),
            raw=data,
        )

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return date_parser.parse(str(value))
        except (ValueError, TypeError):
            return None
