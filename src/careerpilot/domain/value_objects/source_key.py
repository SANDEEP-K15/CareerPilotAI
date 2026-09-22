"""Provider-neutral job source identifier.

This is not JobSourcePort (M2) and is not a catalog of vendors. Any adapter
may persist a source key such as ``example_board`` later without the domain
knowing those vendors exist.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from careerpilot.domain.errors import InvalidJobError

_SOURCE_KEY = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


@dataclass(frozen=True, slots=True)
class SourceKey:
    value: str

    def __post_init__(self) -> None:
        if not _SOURCE_KEY.fullmatch(self.value):
            raise InvalidJobError(
                "source must be a lowercase identifier matching [a-z][a-z0-9_]{0,62}."
            )

    @classmethod
    def parse(cls, raw: str) -> SourceKey:
        normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
        return cls(value=normalized)

    def __str__(self) -> str:
        return self.value
