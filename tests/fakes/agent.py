from __future__ import annotations

from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput


class StubAgent:
    """Deterministic AgentPort for tests. Not a production agent."""

    def __init__(
        self,
        name: str,
        *,
        description: str = "stub agent",
        fail_with: BaseException | None = None,
    ) -> None:
        self._key = AgentKey.parse(name)
        self._description = description
        self._fail_with = fail_with

    @property
    def agent_key(self) -> AgentKey:
        return self._key

    @property
    def description(self) -> str:
        return self._description

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        if self._fail_with is not None:
            raise self._fail_with
        return AgentOutput(
            summary=f"handled {agent_input.intent}",
            data={
                "intent": agent_input.intent,
                "user_id": str(context.user_id) if context.user_id else None,
                **dict(agent_input.parameters),
            },
            notes=(f"agent={self._key.value}",),
        )


class CodedFailureAgent(StubAgent):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        del agent_input, context
        raise AgentExecutionError("task rejected", code="task_rejected")
