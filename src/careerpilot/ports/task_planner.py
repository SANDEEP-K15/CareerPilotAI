"""Planning contracts. M12 uses deterministic planners; M13 may add LLM planners."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext


@dataclass(frozen=True, slots=True)
class UserTaskRequest:
    """User-facing task: intent plus optional parameters and execution context."""

    intent: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    context: AgentContext = field(default_factory=AgentContext)


@dataclass(frozen=True, slots=True)
class PlannedStep:
    """One agent invocation in an execution plan."""

    step_id: str
    agent: AgentKey
    agent_intent: str
    parameters: Mapping[str, object] = field(default_factory=dict)
    inject_job_ids_from: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Ordered multi-step plan produced by a planner."""

    plan_id: str
    description: str
    steps: tuple[PlannedStep, ...]


class TaskPlannerPort(Protocol):
    def plan(self, request: UserTaskRequest) -> ExecutionPlan:
        """Build an execution plan for the request. Raises on unknown intents."""
        ...
