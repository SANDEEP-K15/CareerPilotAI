from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import uuid4

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.worker.messages import (
    LOAD_EXISTING,
    LOAD_PROFILE,
    RANK_AND_PERSIST,
    SEARCH_SOURCES,
    DailyDiscoveryRequest,
    DailyDiscoveryResult,
    FailureSnapshot,
    PersistDiscoveryRequest,
    ProfileSnapshot,
    SearchSnapshot,
    daily_discovery_workflow_id,
)
from careerpilot.worker.workflows import DailyJobDiscoveryWorkflow

QUEUE = "daily-discovery-test"


def _named(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        return activity.defn(name=name)(fn)

    return decorate


def test_workflow_id_is_stable() -> None:
    assert (
        daily_discovery_workflow_id("user", "2026-10-01")
        == "daily-job-discovery-user-2026-10-01"
    )


class ScriptedActivities:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.calls: list[str] = []
        self.search_failures_left = 1 if mode == "retry" else 0
        self.persisted: PersistDiscoveryRequest | None = None

    @_named(LOAD_EXISTING)
    async def load_existing(self, request: DailyDiscoveryRequest) -> DailyDiscoveryResult:
        del request
        self.calls.append("existing")
        if self.mode == "already_done":
            return DailyDiscoveryResult(
                found=True,
                discovery_id="stored",
                selected_job_ids=["job-1"],
                explanation="stored",
            )
        return DailyDiscoveryResult(found=False)

    @_named(LOAD_PROFILE)
    async def load_profile(self, request: DailyDiscoveryRequest) -> ProfileSnapshot:
        self.calls.append("profile")
        if self.mode == "missing_profile":
            raise CareerProfileNotFoundError(request.user_id)
        return ProfileSnapshot(profile_id="profile", searchable=self.mode != "unsearchable")

    @_named(SEARCH_SOURCES)
    async def search(self, request: DailyDiscoveryRequest) -> SearchSnapshot:
        del request
        self.calls.append("search")
        if self.search_failures_left:
            self.search_failures_left -= 1
            raise RuntimeError("temporary outage")
        if self.mode == "empty":
            return SearchSnapshot()
        if self.mode == "provider_failure":
            return SearchSnapshot(
                job_ids=["job-a"],
                failures=[
                    FailureSnapshot(source="beta", code="timeout", message="Job source timed out.")
                ],
            )
        if self.mode == "multi":
            return SearchSnapshot(job_ids=["job-a", "job-b"])
        return SearchSnapshot(job_ids=["job-a"])

    @_named(RANK_AND_PERSIST)
    async def persist(self, request: PersistDiscoveryRequest) -> DailyDiscoveryResult:
        self.calls.append("persist")
        self.persisted = request
        return DailyDiscoveryResult(
            found=True,
            discovery_id="new",
            selected_job_ids=list(request.job_ids),
            failure_sources=[item.source for item in request.failures],
            explanation="scripted",
            considered=len(request.job_ids),
        )

    def bindings(self) -> list[Callable[..., Any]]:
        return [self.load_existing, self.load_profile, self.search, self.persist]


@pytest.fixture
async def temporal_env() -> AsyncIterator[WorkflowEnvironment]:
    started: Any = None
    try:
        started = await WorkflowEnvironment.start_time_skipping()
        env = await started.__aenter__()
    except Exception as exc:
        pytest.skip(f"Temporal test server unavailable: {exc}")
    try:
        yield env
    finally:
        if started is not None:
            await started.__aexit__(None, None, None)


async def _run(
    env: WorkflowEnvironment, script: ScriptedActivities, workflow_id: str
) -> DailyDiscoveryResult:
    async with Worker(
        env.client,
        task_queue=QUEUE,
        workflows=[DailyJobDiscoveryWorkflow],
        activities=script.bindings(),
    ):
        return await env.client.execute_workflow(
            DailyJobDiscoveryWorkflow.run,
            DailyDiscoveryRequest(user_id=str(uuid4()), run_on="2026-10-01"),
            id=workflow_id,
            task_queue=QUEUE,
        )


@pytest.mark.temporal
async def test_workflow_orders_search_before_persist(temporal_env: WorkflowEnvironment) -> None:
    script = ScriptedActivities("multi")
    result = await _run(temporal_env, script, f"discovery-{uuid4()}")
    assert script.calls == ["existing", "profile", "search", "persist"]
    assert result.selected_job_ids == ["job-a", "job-b"]
    assert script.persisted is not None
    assert script.persisted.job_ids == ["job-a", "job-b"]


@pytest.mark.temporal
async def test_workflow_retries_search_then_persists(temporal_env: WorkflowEnvironment) -> None:
    script = ScriptedActivities("retry")
    result = await _run(temporal_env, script, f"discovery-{uuid4()}")
    assert script.calls.count("search") == 2
    assert result.selected_job_ids == ["job-a"]
    assert script.calls[-1] == "persist"


@pytest.mark.temporal
async def test_workflow_returns_stored_run_without_searching(
    temporal_env: WorkflowEnvironment,
) -> None:
    script = ScriptedActivities("already_done")
    result = await _run(temporal_env, script, f"discovery-{uuid4()}")
    assert result.discovery_id == "stored"
    assert script.calls == ["existing"]


@pytest.mark.temporal
async def test_duplicate_workflow_id_is_rejected(temporal_env: WorkflowEnvironment) -> None:
    script = ScriptedActivities("empty")
    workflow_id = daily_discovery_workflow_id(str(uuid4()), "2026-10-01")
    request = DailyDiscoveryRequest(user_id=str(uuid4()), run_on="2026-10-01")
    async with Worker(
        temporal_env.client,
        task_queue=QUEUE,
        workflows=[DailyJobDiscoveryWorkflow],
        activities=script.bindings(),
    ):
        first = await temporal_env.client.execute_workflow(
            DailyJobDiscoveryWorkflow.run,
            request,
            id=workflow_id,
            task_queue=QUEUE,
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )
        with pytest.raises(WorkflowAlreadyStartedError):
            await temporal_env.client.start_workflow(
                DailyJobDiscoveryWorkflow.run,
                request,
                id=workflow_id,
                task_queue=QUEUE,
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
    assert first.selected_job_ids == []


@pytest.mark.temporal
async def test_missing_profile_does_not_search_or_persist(
    temporal_env: WorkflowEnvironment,
) -> None:
    script = ScriptedActivities("missing_profile")
    with pytest.raises(WorkflowFailureError):
        await _run(temporal_env, script, f"discovery-{uuid4()}")
    assert script.calls == ["existing", "profile"]


@pytest.mark.temporal
async def test_empty_and_provider_failure_are_recorded(
    temporal_env: WorkflowEnvironment,
) -> None:
    empty = ScriptedActivities("empty")
    empty_result = await _run(temporal_env, empty, f"discovery-{uuid4()}")
    assert empty_result.selected_job_ids == []
    assert empty.persisted is not None
    assert empty.persisted.job_ids == []

    failed = ScriptedActivities("provider_failure")
    failed_result = await _run(temporal_env, failed, f"discovery-{uuid4()}")
    assert failed_result.selected_job_ids == ["job-a"]
    assert failed_result.failure_sources == ["beta"]
    assert failed.persisted is not None
    assert failed.persisted.failures[0].source == "beta"


@pytest.mark.temporal
async def test_unsearchable_profile_skips_sources(temporal_env: WorkflowEnvironment) -> None:
    script = ScriptedActivities("unsearchable")
    await _run(temporal_env, script, f"discovery-{uuid4()}")
    assert "search" not in script.calls
    assert script.persisted is not None
    assert script.persisted.searchable is False
    assert script.persisted.job_ids == []
