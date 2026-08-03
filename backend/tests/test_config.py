import pytest
from pydantic import ValidationError

from app.config import Settings, normalize_database_url


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


def test_settings_rejects_empty_database_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "")
    with pytest.raises(ValidationError):
        Settings()
