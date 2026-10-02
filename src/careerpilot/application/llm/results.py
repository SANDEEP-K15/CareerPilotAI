from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.ports.llm import LlmResponse


class LlmCompletionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class LlmCompletionResult:
    provider: str
    model: LlmModelId
    status: LlmCompletionStatus
    response: LlmResponse | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is LlmCompletionStatus.SUCCESS
