"""Provider-neutral agent identifier. Not an LLM vendor or model name."""

from __future__ import annotations

import re
from dataclasses import dataclass

from careerpilot.domain.errors import InvalidAgentError

_AGENT_KEY = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


@dataclass(frozen=True, slots=True)
class AgentKey:
    value: str

    def __post_init__(self) -> None:
        if not _AGENT_KEY.fullmatch(self.value):
            raise InvalidAgentError(
                "agent must be a lowercase identifier matching [a-z][a-z0-9_]{0,62}."
            )

    @classmethod
    def parse(cls, raw: str) -> AgentKey:
        normalized = raw.strip().lower().replace("-", "_").replace(" ", "_")
        return cls(value=normalized)

    def __str__(self) -> str:
        return self.value
