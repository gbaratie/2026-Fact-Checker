import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_database_url, prepare_database_url


def test_normalize_adds_asyncpg_driver():
    assert (
        normalize_database_url("postgresql://user:pass@host/db")
        == "postgresql+asyncpg://user:pass@host/db"
    )


def test_normalize_keeps_asyncpg_driver():
    url = "postgresql+asyncpg://user:pass@host/db"
    assert normalize_database_url(url) == url


def test_normalize_postgres_scheme():
    assert (
        normalize_database_url("postgres://user:pass@host/db")
        == "postgresql+asyncpg://user:pass@host/db"
    )


def test_strips_sslmode_and_enables_ssl_connect_args():
    url, connect_args = prepare_database_url(
        "postgresql://user:pass@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+asyncpg://user:pass@ep-x.eu-central-1.aws.neon.tech/neondb"
    assert "sslmode" not in url
    assert connect_args == {"ssl": True}


def test_local_url_has_no_ssl_connect_args():
    _, connect_args = prepare_database_url(
        "postgresql+asyncpg://factchecker:factchecker@localhost:5432/factchecker"
    )
    assert connect_args == {}


def test_settings_rejects_empty_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(ValidationError):
        Settings()


def test_settings_neon_url_exposes_ssl_connect_args(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require",
    )
    settings = Settings()
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in settings.database_url
    assert settings.database_connect_args == {"ssl": True}
