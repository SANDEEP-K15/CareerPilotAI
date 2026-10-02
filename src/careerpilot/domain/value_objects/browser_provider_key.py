"""Provider-neutral browser automation backend identifier."""

from __future__ import annotations

import re
from dataclasses import dataclass

from careerpilot.domain.errors import InvalidBrowserProviderError

_PROVIDER_KEY = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


@dataclass(frozen=True, slots=True)
class BrowserProviderKey:
    value: str

    def __post_init__(self) -> None:
        if not _PROVIDER_KEY.fullmatch(self.value):
            raise InvalidBrowserProviderError(
                "Browser provider must match [a-z][a-z0-9_]{0,62}."
            )

    @classmethod
    def parse(cls, raw: str) -> BrowserProviderKey:
        normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
        return cls(value=normalized)

    def __str__(self) -> str:
        return self.value
