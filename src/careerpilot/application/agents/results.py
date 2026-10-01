from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentOutput


class AgentRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    agent: AgentKey
    status: AgentRunStatus
    output: AgentOutput | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is AgentRunStatus.SUCCESS
