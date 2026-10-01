from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource
from tests.fakes.repositories import InMemoryJobRepository

from careerpilot.application.agents import (
    JOB_SEARCH_AGENT_KEY,
    AgentRegistry,
    AgentTask,
    ExecuteAgentTaskUseCase,
    build_job_search_agent,
)
from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.agents.job_search.agent import JobSearchAgent
from careerpilot.application.agents.job_search.parsing import parse_search_command
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput
from careerpilot.ports.job_source import JobSourceError, JobSourceErrorCode, RawJob


def _raw(source: str, external_id: str) -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title="ML Intern",
        company_name="Acme",
        location="London",
        description="Python and SQL.",
    )


def _agent(*sources: InMemoryJobSource) -> JobSearchAgent:
    job_id = uuid4()
    return build_job_search_agent(
        registry=JobSourceRegistry(sources),
        jobs=InMemoryJobRepository(),
        clock=FrozenClock(),
        ids=FixedIdGenerator(job_id),
    )


def _jobs(output: AgentOutput) -> tuple[dict[str, object], ...]:
    return cast(tuple[dict[str, object], ...], output.data["jobs"])


def _failures(output: AgentOutput) -> tuple[dict[str, object], ...]:
    return cast(tuple[dict[str, object], ...], output.data["failures"])


async def test_job_search_agent_ingests_and_returns_structured_jobs() -> None:
    job_id = uuid4()
    agent = build_job_search_agent(
        registry=JobSourceRegistry((InMemoryJobSource("alpha", (_raw("alpha", "1"),)),)),
        jobs=InMemoryJobRepository(),
        clock=FrozenClock(),
        ids=FixedIdGenerator(job_id),
    )
    output = await agent.run(
        AgentInput(
            intent="search",
            parameters={"keywords": ["ML intern"], "location": "London"},
        ),
        AgentContext(correlation_id="run-1"),
    )
    assert output.summary == "Job search ingested 1 job(s)."
    jobs = _jobs(output)
    assert jobs[0]["id"] == str(job_id)
    assert jobs[0]["source"] == "alpha"
    assert output.data["job_ids"] == [str(job_id)]


async def test_job_search_agent_uses_intent_as_keyword_fallback() -> None:
    output = await _agent(InMemoryJobSource("alpha", (_raw("alpha", "1"),))).run(
        AgentInput(intent="ML intern", parameters={"location": "London"}),
        AgentContext(),
    )
    assert len(_jobs(output)) == 1


async def test_job_search_agent_survives_isolated_provider_failure() -> None:
    alpha = InMemoryJobSource("alpha", (_raw("alpha", "1"),))
    beta = InMemoryJobSource(
        "beta",
        (),
        fail_with=JobSourceError(
            "Job source timed out.",
            code=JobSourceErrorCode.TIMEOUT,
            source="beta",
            retryable=True,
        ),
    )
    output = await _agent(alpha, beta).run(
        AgentInput(intent="search", parameters={"keywords": ["intern"]}),
        AgentContext(),
    )
    assert len(_jobs(output)) == 1
    failures = _failures(output)
    assert failures[0]["source"] == "beta"
    assert failures[0]["code"] == "timeout"
    assert "secret" not in output.summary


async def test_job_search_agent_does_not_leak_runtime_exception_text() -> None:
    source = InMemoryJobSource(
        "alpha",
        fail_with=RuntimeError("secret-token-must-not-leak"),
    )
    output = await _agent(source).run(
        AgentInput(intent="search", parameters={"keywords": ["intern"]}),
        AgentContext(),
    )
    assert _jobs(output) == ()
    assert _failures(output)[0]["message"] == "Job source failed."
    assert "secret-token" not in str(output.data)


async def test_execute_agent_task_runs_registered_job_search_agent() -> None:
    job_id = uuid4()
    agent = build_job_search_agent(
        registry=JobSourceRegistry((InMemoryJobSource("alpha", (_raw("alpha", "1"),)),)),
        jobs=InMemoryJobRepository(),
        clock=FrozenClock(),
        ids=FixedIdGenerator(job_id),
    )
    registry = AgentRegistry((agent,))
    result = await ExecuteAgentTaskUseCase(registry=registry).execute(
        AgentTask(
            agent=JOB_SEARCH_AGENT_KEY.value,
            agent_input=AgentInput(intent="search", parameters={"keywords": ["intern"]}),
            context=AgentContext(),
        )
    )
    assert result.succeeded
    assert result.agent == JOB_SEARCH_AGENT_KEY
    assert result.output is not None
    assert result.output.data["job_ids"] == [str(job_id)]


async def test_invalid_search_query_returns_structured_failure() -> None:
    agent = _agent(InMemoryJobSource("alpha", (_raw("alpha", "1"),)))
    registry = AgentRegistry((agent,))
    result = await ExecuteAgentTaskUseCase(registry=registry).execute(
        AgentTask(
            agent="job_search",
            agent_input=AgentInput(intent="search", parameters={}),
            context=AgentContext(),
        )
    )
    assert not result.succeeded
    assert result.error_code == "invalid_job_search_query"


def test_parse_search_command_rejects_empty_sources_list() -> None:
    with pytest.raises(AgentExecutionError) as exc:
        parse_search_command(
            AgentInput(intent="search", parameters={"keywords": ["x"], "sources": []})
        )
    assert exc.value.code == "invalid_job_search_query"
