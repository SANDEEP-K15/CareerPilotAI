from __future__ import annotations

from dataclasses import dataclass

from careerpilot.application.agents.errors import (
    InvalidAgentTaskError,
    normalize_agent_failure,
)
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.agents.results import AgentRunResult, AgentRunStatus
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext, AgentInput


@dataclass(frozen=True, slots=True)
class AgentTask:
    agent: str | AgentKey
    agent_input: AgentInput
    context: AgentContext


class ExecuteAgentTaskUseCase:
    """Run one registered agent. Registry misses raise; agent failures return results."""

    def __init__(self, *, registry: AgentRegistry) -> None:
        self._registry = registry

    async def execute(self, task: AgentTask) -> AgentRunResult:
        intent = " ".join(task.agent_input.intent.split())
        if not intent:
            raise InvalidAgentTaskError("intent is required.")
        key = (
            task.agent
            if isinstance(task.agent, AgentKey)
            else AgentKey.parse(task.agent)
        )
        port = self._registry.get(key)
        try:
            output = await port.run(
                AgentInput(intent=intent, parameters=dict(task.agent_input.parameters)),
                task.context,
            )
        except Exception as exc:
            error = normalize_agent_failure(key.value, exc)
            return AgentRunResult(
                agent=key,
                status=AgentRunStatus.FAILED,
                error_code=error.code,
                error_message=error.message,
            )
        return AgentRunResult(agent=key, status=AgentRunStatus.SUCCESS, output=output)
