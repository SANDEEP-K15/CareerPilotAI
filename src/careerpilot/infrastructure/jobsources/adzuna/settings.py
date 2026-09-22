from __future__ import annotations

import re

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_COUNTRY = re.compile(r"^[a-z]{2}$")


class AdzunaSettings(BaseSettings):
    """Optional Adzuna credentials. Empty values mean the adapter is disabled."""

    model_config = SettingsConfigDict(env_prefix="ADZUNA__", extra="ignore")

    app_id: SecretStr = Field(default=SecretStr(""))
    app_key: SecretStr = Field(default=SecretStr(""))
    country: str = Field(default="gb")
    base_url: str = Field(default="https://api.adzuna.com/v1/api")
    timeout_seconds: float = Field(default=15.0, gt=0, le=60)

    @field_validator("country")
    @classmethod
    def country_must_be_iso_alpha2(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not _COUNTRY.fullmatch(normalized):
            raise ValueError("ADZUNA__COUNTRY must be a two-letter country code such as gb or in.")
        return normalized

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_https_adzuna(cls, value: str) -> str:
        url = value.rstrip("/")
        if not url.startswith("https://"):
            raise ValueError("ADZUNA__BASE_URL must use https.")
        return url

    @property
    def credentials_configured(self) -> bool:
        return bool(self.app_id.get_secret_value() and self.app_key.get_secret_value())
