from __future__ import annotations

from uuid import uuid4

import pytest
from tests.fakes.agent import CodedFailureAgent, StubAgent

from careerpilot.application.agents.execution import ExecuteAgentTaskUseCase
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.orchestration import (
    DeterministicTaskPlanner,
    Executive,
    TaskRouter,
    UnknownOrchestrationIntentError,
    UserTaskRequest,
    build_executive,
)
from careerpilot.application.orchestration.errors import InvalidOrchestrationPlanError
from careerpilot.application.orchestration.results import OrchestrationStatus
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput


class JobSearchStub:
    """Returns deterministic job_ids for orchestration chaining tests."""

    def __init__(self) -> None:
        self._key = AgentKey.parse("job_search")

    @property
    def agent_key(self) -> AgentKey:
        return self._key

    @property
    def description(self) -> str:
        return "stub job search"

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        del context
        return AgentOutput(
            summary="stub search",
            data={
                "job_ids": ["11111111-1111-4111-8111-111111111111"],
                "intent": agent_input.intent,
            },
        )


class JobRankingStub:
    def __init__(self) -> None:
        self._key = AgentKey.parse("job_ranking")
        self.last_job_ids: tuple[str, ...] | None = None

    @property
    def agent_key(self) -> AgentKey:
        return self._key

    @property
    def description(self) -> str:
        return "stub job ranking"

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        del context
        raw = agent_input.parameters.get("job_ids", [])
        self.last_job_ids = tuple(str(item) for item in raw) if isinstance(raw, list) else ()
        return AgentOutput(summary="stub rank", data={"rankings": []})


def test_planner_routes_registered_agent_intent() -> None:
    registry = AgentRegistry((StubAgent("job_search"),))
    plan = DeterministicTaskPlanner(registry=registry).plan(
        UserTaskRequest(intent="job_search", parameters={"keywords": ("python",)})
    )
    assert plan.plan_id == "direct_job_search"
    assert len(plan.steps) == 1
    assert plan.steps[0].agent_intent == "search_jobs"
    assert plan.steps[0].parameters["keywords"] == ("python",)


def test_planner_builds_search_and_rank_plan() -> None:
    registry = AgentRegistry((JobSearchStub(), JobRankingStub()))
    plan = DeterministicTaskPlanner(registry=registry).plan(
        UserTaskRequest(intent="search_and_rank", parameters={"keywords": ("go",)})
    )
    assert plan.plan_id == "search_and_rank"
    assert [step.step_id for step in plan.steps] == ["search", "rank"]
    assert plan.steps[1].inject_job_ids_from == "search"


def test_planner_unknown_intent_raises() -> None:
    with pytest.raises(UnknownOrchestrationIntentError):
        DeterministicTaskPlanner(registry=AgentRegistry()).plan(UserTaskRequest(intent="fly"))


def test_planner_explicit_steps_require_registered_agents() -> None:
    registry = AgentRegistry((StubAgent("alpha"),))
    with pytest.raises(InvalidOrchestrationPlanError):
        DeterministicTaskPlanner(registry=registry).plan(
            UserTaskRequest(
                intent="custom",
                parameters={"steps": [{"agent": "missing", "intent": "run"}]},
            )
        )


async def test_executive_runs_direct_agent() -> None:
    registry = AgentRegistry((StubAgent("helper"),))
    executive = build_executive(registry=registry)
    result = await executive.run(
        UserTaskRequest(intent="helper", parameters={"value": 2}, context=AgentContext())
    )
    assert result.succeeded
    assert result.plan_id == "direct_helper"
    assert result.output is not None
    assert result.output.data["value"] == 2


async def test_executive_chains_search_and_rank() -> None:
    ranking = JobRankingStub()
    registry = AgentRegistry((JobSearchStub(), ranking))
    result = await build_executive(registry=registry).run(
        UserTaskRequest(
            intent="search_then_rank",
            parameters={"keywords": ("rust",)},
            context=AgentContext(user_id=uuid4()),
        )
    )
    assert result.succeeded
    assert len(result.steps) == 2
    assert ranking.last_job_ids == ("11111111-1111-4111-8111-111111111111",)


async def test_executive_stops_on_agent_failure() -> None:
    registry = AgentRegistry((CodedFailureAgent("helper"),))
    result = await build_executive(registry=registry).run(UserTaskRequest(intent="helper"))
    assert result.status is OrchestrationStatus.FAILED
    assert result.error_code == "task_rejected"
    assert len(result.steps) == 1


async def test_task_router_merges_explicit_and_discovered_job_ids() -> None:
    registry = AgentRegistry((StubAgent("job_ranking"),))
    router = TaskRouter(registry=registry)
    prior = {
        "search": AgentOutput(
            summary="search",
            data={"job_ids": ["22222222-2222-4222-8222-222222222222"]},
        )
    }
    from careerpilot.ports.task_planner import PlannedStep

    task = router.build_task(
        PlannedStep(
            step_id="rank",
            agent=AgentKey.parse("job_ranking"),
            agent_intent="rank",
            parameters={"job_ids": ["11111111-1111-4111-8111-111111111111"]},
            inject_job_ids_from="search",
        ),
        context=AgentContext(user_id=uuid4()),
        prior_outputs=prior,
    )
    job_ids = task.agent_input.parameters["job_ids"]
    assert job_ids == [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
    ]


async def test_executive_is_independently_wired() -> None:
    registry = AgentRegistry((StubAgent("alpha"), StubAgent("beta")))
    executive = Executive(
        planner=DeterministicTaskPlanner(registry=registry),
        router=TaskRouter(registry=registry),
        executor=ExecuteAgentTaskUseCase(registry=registry),
    )
    result = await executive.run(
        UserTaskRequest(
            intent="custom",
            parameters={
                "steps": [
                    {"agent": "alpha", "step_id": "one", "intent": "first"},
                    {"agent": "beta", "step_id": "two", "intent": "second"},
                ]
            },
        )
    )
    assert result.succeeded
    assert len(result.steps) == 2
