"""Deterministic Temporal orchestration. I/O stays in activities."""

from datetime import timedelta
from typing import cast

from temporalio import workflow
from temporalio.common import RetryPolicy

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
)

_DB_RETRY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(milliseconds=100),
    non_retryable_error_types=["CareerProfileNotFoundError", "InvalidDiscoveryQueryError"],
)
_PROFILE_RETRY = RetryPolicy(
    maximum_attempts=1,
    non_retryable_error_types=["CareerProfileNotFoundError", "InvalidDiscoveryQueryError"],
)
_SEARCH_RETRY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(milliseconds=100),
    non_retryable_error_types=["InvalidDiscoveryQueryError"],
)


@workflow.defn(name="DailyJobDiscoveryWorkflow")
class DailyJobDiscoveryWorkflow:
    @workflow.run
    async def run(self, request: DailyDiscoveryRequest) -> DailyDiscoveryResult:
        existing = await workflow.execute_activity(
            LOAD_EXISTING,
            request,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_DB_RETRY,
            result_type=DailyDiscoveryResult,
        )
        if existing.found:
            return cast(DailyDiscoveryResult, existing)

        profile = await workflow.execute_activity(
            LOAD_PROFILE,
            request,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=_PROFILE_RETRY,
            result_type=ProfileSnapshot,
        )
        job_ids: list[str] = []
        failures: list[FailureSnapshot] = []
        if profile.searchable:
            searched = await workflow.execute_activity(
                SEARCH_SOURCES,
                request,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=_SEARCH_RETRY,
                result_type=SearchSnapshot,
            )
            job_ids = list(searched.job_ids)
            failures = list(searched.failures)
        persisted = await workflow.execute_activity(
            RANK_AND_PERSIST,
            PersistDiscoveryRequest(
                user_id=request.user_id,
                run_on=request.run_on,
                threshold=request.threshold,
                limit=request.limit,
                searchable=profile.searchable,
                job_ids=job_ids,
                failures=failures,
            ),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=_DB_RETRY,
            result_type=DailyDiscoveryResult,
        )
        return cast(DailyDiscoveryResult, persisted)
