from __future__ import annotations

import pytest
from pydantic import ValidationError

from careerpilot.config.settings import Settings, get_settings


def test_settings_accept_test_environment_without_production_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SECURITY__SECRET_KEY", "replace-with-a-long-random-value")
    monkeypatch.setenv(
        "DATABASE__URL",
        "postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot",
    )
    get_settings.cache_clear()
    settings = Settings()
    assert settings.environment.value == "test"


def test_production_rejects_placeholder_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECURITY__SECRET_KEY", "replace-with-a-long-random-value")
    with pytest.raises(ValidationError):
        Settings()


def test_database_url_must_be_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE__URL", "sqlite+aiosqlite:///./test.db")
    with pytest.raises(ValidationError):
        Settings()
