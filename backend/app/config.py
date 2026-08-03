from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
