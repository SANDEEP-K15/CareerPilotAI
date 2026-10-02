"""Cost observation contracts. Amounts come from providers only (ADR 0011)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.llm import LlmUsage


@dataclass(frozen=True, slots=True)
class LlmUsageEvent:
    provider: LlmProviderKey
    model: LlmModelId
    usage: LlmUsage
    correlation_id: str | None = None
    user_id: str | None = None
    task: str | None = None


class CostManagerPort(Protocol):
    async def record_llm_usage(self, event: LlmUsageEvent) -> None:
        """Record usage. Failures must not abort the caller unless policy requires it."""
        ...
