from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from tests.fakes.repositories import InMemoryCareerProfileRepository, InMemoryJobRepository

from careerpilot.application.agents import (
    JOB_RANKING_AGENT_KEY,
    AgentRegistry,
    AgentTask,
    ExecuteAgentTaskUseCase,
    build_job_ranking_agent,
)
from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.agents.job_ranking.agent import JobRankingAgent
from careerpilot.application.agents.job_ranking.parsing import require_user_id
from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput


def _profile(user_id: UUID) -> CareerProfile:
    return CareerProfile.new(
        profile_id=uuid4(),
        user_id=user_id,
        now=datetime(2026, 10, 1, tzinfo=UTC),
        skills=("Python", "SQL"),
        target_titles=("ML Intern",),
        locations=("London",),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
    )


def _job(**overrides: object) -> Job:
    payload: dict[str, object] = {
        "job_id": uuid4(),
        "source": SourceKey.parse("example_board"),
        "external_id": str(uuid4()),
        "title": "ML Intern",
        "company_name": "Acme",
        "discovered_at": datetime(2026, 10, 1, tzinfo=UTC),
        "description": "Use Python and SQL daily.",
        "location": "London",
        "remote_policy": RemotePolicy.REMOTE,
        "employment_type": EmploymentType.INTERNSHIP,
    }
    payload.update(overrides)
    return Job.new(**payload)  # type: ignore[arg-type]


def _rankings(output: AgentOutput) -> tuple[dict[str, object], ...]:
    return cast(tuple[dict[str, object], ...], output.data["rankings"])


async def _wired(
    user_id: UUID, *jobs: Job
) -> tuple[JobRankingAgent, InMemoryJobRepository]:
    profiles = InMemoryCareerProfileRepository()
    job_repo = InMemoryJobRepository()
    await profiles.add(_profile(user_id))
    for job in jobs:
        await job_repo.add(job)
    return build_job_ranking_agent(profiles=profiles, jobs=job_repo), job_repo


async def test_job_ranking_agent_returns_scores_and_reasons() -> None:
    user_id = uuid4()
    job = _job()
    agent, _repo = await _wired(user_id, job)
    output = await agent.run(
        AgentInput(intent="rank", parameters={"job_ids": [str(job.id)]}),
        AgentContext(user_id=user_id),
    )
    rankings = _rankings(output)
    assert rankings[0]["score"] == 100
    assert "Python" in str(rankings[0]["matched_skills"])
    assert output.data["ranked_job_ids"] == [str(job.id)]


async def test_ranking_order_is_score_then_job_id() -> None:
    user_id = uuid4()
    strong = _job(description="Use Python and SQL daily.")
    partial = _job(description="Python intern role.")
    agent, _ = await _wired(user_id, partial, strong)
    output = await agent.run(
        AgentInput(intent="rank", parameters={"job_ids": [str(partial.id), str(strong.id)]}),
        AgentContext(user_id=user_id),
    )
    assert [item["job_id"] for item in _rankings(output)] == [str(strong.id), str(partial.id)]


async def test_tie_breaks_by_job_id_string() -> None:
    user_id = uuid4()
    first = _job()
    second = _job()
    low, high = sorted((first.id, second.id), key=str)
    agent, _ = await _wired(user_id, first, second)
    output = await agent.run(
        AgentInput(
            intent="rank",
            parameters={"job_ids": [str(first.id), str(second.id)], "threshold": 0},
        ),
        AgentContext(user_id=user_id),
    )
    assert [item["job_id"] for item in _rankings(output)] == [str(low), str(high)]


async def test_threshold_filters_weak_jobs() -> None:
    user_id = uuid4()
    strong = _job()
    weak = _job(
        title="Accountant",
        description="Spreadsheets only.",
        remote_policy=RemotePolicy.UNSPECIFIED,
        employment_type=EmploymentType.UNSPECIFIED,
        location=None,
    )
    agent, _ = await _wired(user_id, strong, weak)
    output = await agent.run(
        AgentInput(
            intent="rank",
            parameters={"job_ids": [str(strong.id), str(weak.id)], "threshold": 95},
        ),
        AgentContext(user_id=user_id),
    )
    assert [item["job_id"] for item in _rankings(output)] == [str(strong.id)]
    assert output.data["rejected"] == 1


async def test_limit_caps_ranked_results() -> None:
    user_id = uuid4()
    jobs = tuple(_job() for _ in range(3))
    agent, _ = await _wired(user_id, *jobs)
    output = await agent.run(
        AgentInput(
            intent="rank",
            parameters={
                "job_ids": [str(job.id) for job in jobs],
                "threshold": 0,
                "limit": 2,
            },
        ),
        AgentContext(user_id=user_id),
    )
    assert len(_rankings(output)) == 2


async def test_invalid_threshold_raises_via_agent() -> None:
    user_id = uuid4()
    job = _job()
    agent, _ = await _wired(user_id, job)
    with pytest.raises(AgentExecutionError) as exc:
        await agent.run(
            AgentInput(
                intent="rank",
                parameters={"job_ids": [str(job.id)], "threshold": 101},
            ),
            AgentContext(user_id=user_id),
        )
    assert exc.value.code == "invalid_match_query"


async def test_invalid_threshold_via_execute_returns_structured_failure() -> None:
    user_id = uuid4()
    job = _job()
    agent, _ = await _wired(user_id, job)
    registry = AgentRegistry((agent,))
    result = await ExecuteAgentTaskUseCase(registry=registry).execute(
        AgentTask(
            agent=JOB_RANKING_AGENT_KEY.value,
            agent_input=AgentInput(
                intent="rank",
                parameters={"job_ids": [str(job.id)], "threshold": 101},
            ),
            context=AgentContext(user_id=user_id),
        )
    )
    assert not result.succeeded
    assert result.error_code == "invalid_match_query"


async def test_empty_job_list_returns_empty_rankings() -> None:
    user_id = uuid4()
    agent, _ = await _wired(user_id)
    output = await agent.run(
        AgentInput(intent="rank", parameters={"job_ids": []}),
        AgentContext(user_id=user_id),
    )
    assert _rankings(output) == ()
    assert output.summary == "No jobs were provided to rank."


async def test_missing_profile_raises() -> None:
    agent = build_job_ranking_agent(
        profiles=InMemoryCareerProfileRepository(),
        jobs=InMemoryJobRepository(),
    )
    with pytest.raises(CareerProfileNotFoundError):
        await agent.run(
            AgentInput(intent="rank", parameters={"job_ids": []}),
            AgentContext(user_id=uuid4()),
        )


async def test_missing_user_context_is_invalid() -> None:
    with pytest.raises(AgentExecutionError) as exc:
        require_user_id(AgentContext())
    assert exc.value.code == "invalid_agent_task"


async def test_ranking_is_deterministic() -> None:
    user_id = uuid4()
    job = _job()
    agent, _ = await _wired(user_id, job)
    params = AgentInput(intent="rank", parameters={"job_ids": [str(job.id)]})
    context = AgentContext(user_id=user_id)
    first = await agent.run(params, context)
    second = await agent.run(params, context)
    assert first == second
