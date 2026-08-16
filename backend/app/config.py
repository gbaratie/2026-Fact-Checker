from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import PrivateAttr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Paramètres libpq passés en kwargs par SQLAlchemy — non supportés par asyncpg.connect()
_ASYNCPG_UNSUPPORTED_QUERY_KEYS = frozenset(
    {
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "sslcrl",
        "channel_binding",
    }
)


def prepare_database_url(url: str) -> tuple[str, dict[str, Any]]:
    """Normalise l'URL pour SQLAlchemy+asyncpg et calcule connect_args (SSL Neon)."""
    cleaned = url.strip().strip('"').strip("'")
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://"):
        cleaned = "postgresql+asyncpg://" + cleaned[len("postgresql://") :]

    parsed = urlparse(cleaned)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    kept: list[tuple[str, str]] = []
    ssl_required = False

    for key, value in query_items:
        lower = key.lower()
        if lower in _ASYNCPG_UNSUPPORTED_QUERY_KEYS:
            if lower == "sslmode" and value.lower() not in {"disable", "allow", "prefer"}:
                ssl_required = True
            continue
        kept.append((key, value))

    host = (parsed.hostname or "").lower()
    if "neon.tech" in host:
        ssl_required = True

    normalized = urlunparse(parsed._replace(query=urlencode(kept)))
    connect_args: dict[str, Any] = {"ssl": True} if ssl_required else {}
    return normalized, connect_args


def normalize_database_url(url: str) -> str:
    """Ensure async SQLAlchemy driver and strip asyncpg-incompatible query params."""
    normalized, _ = prepare_database_url(url)
    return normalized


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://factchecker:factchecker@localhost:5432/factchecker"
    youtube_api_key: str = ""
    ingestion_secret: str = "dev-secret"
    cors_origins: str = "http://localhost:5173"

    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    clair_api_base: str = "https://clair-production.up.railway.app/api/v1"
    an_votes_url: str = (
        "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json"
    )

    rss_feeds: list[str] = [
        # Politique — titres nationaux
        "https://www.lemonde.fr/politique/rss_full.xml",
        "https://www.franceinfo.fr/politique.rss",
        "https://www.lefigaro.fr/rss/figaro_politique.xml",
        "https://www.liberation.fr/arc/outboundfeeds/rss/category/politique/",
        "https://www.lexpress.fr/rss/politique.xml",
        "https://www.nouvelobs.com/politique/rss.xml",
        "https://www.leparisien.fr/politique/rss.xml",
        "https://www.20minutes.fr/feeds/rss-politique.xml",
        # TV / radio / institutions
        "https://www.bfmtv.com/rss/politique/",
        "https://www.france24.com/fr/france/rss",
        "https://www.publicsenat.fr/rss",
        # Indépendants / spécialisés
        "https://www.mediapart.fr/articles/feed",
        "https://www.politico.eu/feed/",
        "https://www.huffingtonpost.fr/feeds/index.xml",
        "https://www.challenges.fr/rss.xml",
        "https://www.slate.fr/rss.xml",
        "https://www.humanite.fr/rss",
        "https://www.la-croix.com/rss",
        # Régional
        "https://www.sudouest.fr/politique/rss.xml",
    ]

    _database_connect_args: dict[str, Any] = PrivateAttr(default_factory=dict)

    @field_validator("database_url")
    @classmethod
    def reject_blank_database_url(cls, value: str) -> str:
        if not value or not value.strip().strip('"').strip("'"):
            raise ValueError(
                "DATABASE_URL manquante ou invalide. "
                "Sur Render, colle la connection string Neon "
                "(ex. postgresql://... ou postgresql+asyncpg://...)."
            )
        return value

    @model_validator(mode="after")
    def normalize_database(self) -> "Settings":
        normalized, connect_args = prepare_database_url(self.database_url)
        if "://" not in normalized:
            raise ValueError("DATABASE_URL manquante ou invalide.")
        self.database_url = normalized
        self._database_connect_args = connect_args
        return self

    @property
    def database_connect_args(self) -> dict[str, Any]:
        return self._database_connect_args

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
