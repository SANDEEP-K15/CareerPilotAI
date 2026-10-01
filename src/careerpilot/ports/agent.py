"""Agent contracts. Implementations orchestrate application services, not vendors."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from careerpilot.domain.value_objects.agent_key import AgentKey


@dataclass(frozen=True, slots=True)
class AgentContext:
    """Read-only execution context passed to every agent run."""

    user_id: UUID | None = None
    correlation_id: str | None = None
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentInput:
    """Task payload for one agent invocation."""

    intent: str
    parameters: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AgentOutput:
    """Structured agent response. No provider-specific fields."""

    summary: str
    data: Mapping[str, object] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


class AgentPort(Protocol):
    @property
    def agent_key(self) -> AgentKey: ...

    @property
    def description(self) -> str: ...

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        """Run one task. Raise AgentExecutionError for expected failures."""
        ...
