"""Runtime configuration. Values come from the environment, never from code secrets."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


_PLACEHOLDER_SECRET = "replace-with-a-long-random-value"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE__", extra="ignore")

    url: str = Field(
        default="postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot",
        description="Async SQLAlchemy URL. Must be PostgreSQL.",
    )
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=100)
    echo: bool = False

    @field_validator("url")
    @classmethod
    def require_postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE__URL must be a PostgreSQL SQLAlchemy URL.")
        return value


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SECURITY__", extra="ignore")

    secret_key: SecretStr = Field(default=SecretStr(_PLACEHOLDER_SECRET))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Field(default=Environment.LOCAL)
    debug: bool = False
    log_level: str = Field(default="INFO")
    log_json: bool = False

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @model_validator(mode="after")
    def production_must_not_use_placeholder_secret(self) -> Settings:
        if self.environment in {Environment.PRODUCTION, Environment.STAGING}:
            secret = self.security.secret_key.get_secret_value()
            if not secret or secret == _PLACEHOLDER_SECRET:
                raise ValueError(
                    "SECURITY__SECRET_KEY must be set to a unique value in "
                    f"{self.environment} environments."
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
