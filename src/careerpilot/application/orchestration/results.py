from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from careerpilot.application.agents.results import AgentRunResult
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentOutput


class OrchestrationStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OrchestrationStepResult:
    step_id: str
    agent: AgentKey
    result: AgentRunResult


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    status: OrchestrationStatus
    intent: str
    plan_id: str
    summary: str
    steps: tuple[OrchestrationStepResult, ...]
    output: AgentOutput | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is OrchestrationStatus.SUCCESS
