from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Ensure async SQLAlchemy driver and strip accidental whitespace/quotes."""
    cleaned = url.strip().strip('"').strip("'")
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql://"):
        cleaned = "postgresql+asyncpg://" + cleaned[len("postgresql://") :]
    return cleaned


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://factchecker:factchecker@localhost:5432/factchecker"
    youtube_api_key: str = ""
    ingestion_secret: str = "dev-secret"
    cors_origins: str = "http://localhost:5173"

    clair_api_base: str = "https://clair-production.up.railway.app/api/v1"
    an_votes_url: str = (
        "https://data.assemblee-nationale.fr/static/openData/repository/17/loi/scrutins/Scrutins.json"
    )

    rss_feeds: list[str] = [
        "https://www.lemonde.fr/politique/rss_full.xml",
        "https://www.franceinfo.fr/politique.rss",
        "https://www.lefigaro.fr/rss/figaro_politique.xml",
    ]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        normalized = normalize_database_url(value)
        if not normalized or "://" not in normalized:
            raise ValueError(
                "DATABASE_URL manquante ou invalide. "
                "Sur Render, colle la connection string Neon "
                "(ex. postgresql://... ou postgresql+asyncpg://...)."
            )
        return normalized

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
