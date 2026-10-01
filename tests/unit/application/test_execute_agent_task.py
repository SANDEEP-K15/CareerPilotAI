from __future__ import annotations

from uuid import uuid4

import pytest
from tests.fakes.agent import CodedFailureAgent, StubAgent

from careerpilot.application.agents.errors import InvalidAgentTaskError, UnknownAgentError
from careerpilot.application.agents.execution import AgentTask, ExecuteAgentTaskUseCase
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.agents.results import AgentRunStatus
from careerpilot.ports.agent import AgentContext, AgentInput


async def test_execute_agent_task_returns_structured_success() -> None:
    registry = AgentRegistry((StubAgent("helper"),))
    use_case = ExecuteAgentTaskUseCase(registry=registry)
    user_id = uuid4()
    result = await use_case.execute(
        AgentTask(
            agent="helper",
            agent_input=AgentInput(intent="echo", parameters={"value": 1}),
            context=AgentContext(user_id=user_id, correlation_id="corr-1"),
        )
    )
    assert result.succeeded
    assert result.output is not None
    assert result.output.summary == "handled echo"
    assert result.output.data["user_id"] == str(user_id)
    assert result.output.data["value"] == 1
    assert result.error_code is None


async def test_execute_agent_task_normalizes_blank_intent() -> None:
    use_case = ExecuteAgentTaskUseCase(registry=AgentRegistry((StubAgent("helper"),)))
    result = await use_case.execute(
        AgentTask(
            agent="helper",
            agent_input=AgentInput(intent="  ping  "),
            context=AgentContext(),
        )
    )
    assert result.output is not None
    assert result.output.data["intent"] == "ping"


async def test_execute_agent_task_requires_intent() -> None:
    use_case = ExecuteAgentTaskUseCase(registry=AgentRegistry((StubAgent("helper"),)))
    with pytest.raises(InvalidAgentTaskError):
        await use_case.execute(
            AgentTask(
                agent="helper",
                agent_input=AgentInput(intent="   "),
                context=AgentContext(),
            )
        )


async def test_unknown_agent_raises() -> None:
    use_case = ExecuteAgentTaskUseCase(registry=AgentRegistry())
    with pytest.raises(UnknownAgentError):
        await use_case.execute(
            AgentTask(
                agent="missing",
                agent_input=AgentInput(intent="run"),
                context=AgentContext(),
            )
        )


async def test_agent_failure_returns_structured_result() -> None:
    registry = AgentRegistry((CodedFailureAgent("helper"),))
    result = await ExecuteAgentTaskUseCase(registry=registry).execute(
        AgentTask(
            agent="helper",
            agent_input=AgentInput(intent="run"),
            context=AgentContext(),
        )
    )
    assert result.status is AgentRunStatus.FAILED
    assert result.error_code == "task_rejected"
    assert result.error_message == "task rejected"
    assert result.output is None


async def test_unexpected_exception_is_normalized_without_leaking_details() -> None:
    registry = AgentRegistry(
        (StubAgent("helper", fail_with=RuntimeError("secret-token-must-not-leak")),)
    )
    result = await ExecuteAgentTaskUseCase(registry=registry).execute(
        AgentTask(
            agent="helper",
            agent_input=AgentInput(intent="run"),
            context=AgentContext(),
        )
    )
    assert result.status is AgentRunStatus.FAILED
    assert result.error_code == "agent_execution_failed"
    assert "secret-token" not in (result.error_message or "")


async def test_agents_are_independently_invokable() -> None:
    registry = AgentRegistry((StubAgent("alpha"), StubAgent("beta")))
    use_case = ExecuteAgentTaskUseCase(registry=registry)
    first = await use_case.execute(
        AgentTask(
            agent="alpha",
            agent_input=AgentInput(intent="one"),
            context=AgentContext(),
        )
    )
    second = await use_case.execute(
        AgentTask(
            agent="beta",
            agent_input=AgentInput(intent="two"),
            context=AgentContext(),
        )
    )
    assert first.output is not None and first.output.summary == "handled one"
    assert second.output is not None and second.output.summary == "handled two"
