from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from careerpilot.application.client_tasks.errors import ClientTaskTimeoutError
from careerpilot.application.orchestration.results import OrchestrationResult
from careerpilot.ports.agent import AgentContext
from careerpilot.ports.task_planner import UserTaskRequest


class ExecutiveRunner(Protocol):
    async def run(self, request: UserTaskRequest) -> OrchestrationResult: ...


@dataclass(frozen=True, slots=True)
class SubmitClientTaskCommand:
    user_id: UUID
    intent: str
    parameters: dict[str, object]
    correlation_id: str | None = None
    request_id: str | None = None


class SubmitClientTaskUseCase:
    """Submit an external client task to the M12 Executive orchestrator."""

    def __init__(self, *, executive: ExecutiveRunner, timeout_seconds: float = 30.0) -> None:
        self._executive = executive
        self._timeout_seconds = timeout_seconds

    async def execute(self, command: SubmitClientTaskCommand) -> OrchestrationResult:
        correlation = command.correlation_id or command.request_id
        context = AgentContext(user_id=command.user_id, correlation_id=correlation)
        request = UserTaskRequest(
            intent=command.intent,
            parameters=command.parameters,
            context=context,
        )
        try:
            return await asyncio.wait_for(
                self._executive.run(request),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            raise ClientTaskTimeoutError(self._timeout_seconds) from exc
