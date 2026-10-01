"""Temporal activities. Each one delegates to the discovery use case."""

from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio import activity

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.discover_daily_jobs import (
    DiscoverDailyJobsUseCase,
    profile_is_searchable,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.daily_discovery import DailyDiscovery, DiscoverySourceFailure
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyCareerProfileRepository,
    SqlAlchemyDailyDiscoveryRepository,
    SqlAlchemyJobRepository,
)
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
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


class DailyDiscoveryActivities:
    def __init__(
        self,
        *,
        sessions: async_sessionmaker[AsyncSession],
        registry: JobSourceRegistry,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._sessions = sessions
        self._registry = registry
        self._clock = clock
        self._ids = ids

    def bindings(self) -> list[Callable[..., Any]]:
        return [
            self.load_existing_daily_discovery,
            self.load_discovery_profile,
            self.search_discovery_sources,
            self.rank_and_persist_daily_discovery,
        ]

    @activity.defn(name=LOAD_EXISTING)
    async def load_existing_daily_discovery(
        self, request: DailyDiscoveryRequest
    ) -> DailyDiscoveryResult:
        async with self._sessions() as session:
            use_case = self._use_case(session)
            existing = await use_case.find_existing(
                UUID(request.user_id), date.fromisoformat(request.run_on)
            )
            result = _result_from(existing)
            await session.commit()
            return result

    @activity.defn(name=LOAD_PROFILE)
    async def load_discovery_profile(self, request: DailyDiscoveryRequest) -> ProfileSnapshot:
        async with self._sessions() as session:
            use_case = self._use_case(session)
            profile = await use_case.load_profile(UUID(request.user_id))
            snapshot = ProfileSnapshot(
                profile_id=str(profile.id),
                searchable=profile_is_searchable(profile),
            )
            await session.commit()
            return snapshot

    @activity.defn(name=SEARCH_SOURCES)
    async def search_discovery_sources(self, request: DailyDiscoveryRequest) -> SearchSnapshot:
        async with self._sessions() as session:
            use_case = self._use_case(session)
            profile = await use_case.load_profile(UUID(request.user_id))
            job_ids, failures = await use_case.search_and_ingest(profile)
            snapshot = SearchSnapshot(
                job_ids=[str(job_id) for job_id in job_ids],
                failures=[
                    FailureSnapshot(source=item.source, code=item.code, message=item.message)
                    for item in failures
                ],
            )
            await session.commit()
            return snapshot

    @activity.defn(name=RANK_AND_PERSIST)
    async def rank_and_persist_daily_discovery(
        self, request: PersistDiscoveryRequest
    ) -> DailyDiscoveryResult:
        async with self._sessions() as session:
            use_case = self._use_case(session)
            stored = await use_case.rank_and_persist(
                user_id=UUID(request.user_id),
                run_on=date.fromisoformat(request.run_on),
                threshold=request.threshold,
                limit=request.limit,
                searchable=request.searchable,
                job_ids=tuple(UUID(job_id) for job_id in request.job_ids),
                failures=tuple(
                    DiscoverySourceFailure(
                        source=item.source, code=item.code, message=item.message
                    )
                    for item in request.failures
                ),
            )
            result = _result_from(stored)
            await session.commit()
            return result

    def _use_case(self, session: AsyncSession) -> DiscoverDailyJobsUseCase:
        jobs = SqlAlchemyJobRepository(session)
        return DiscoverDailyJobsUseCase(
            profiles=SqlAlchemyCareerProfileRepository(session),
            jobs=jobs,
            discoveries=SqlAlchemyDailyDiscoveryRepository(session),
            search=SearchAndIngestJobsUseCase(
                search_sources=SearchRegisteredSourcesUseCase(registry=self._registry),
                ingest=IngestRawJobUseCase(jobs=jobs, clock=self._clock, ids=self._ids),
            ),
            clock=self._clock,
            ids=self._ids,
        )


def _result_from(discovery: DailyDiscovery | None) -> DailyDiscoveryResult:
    if discovery is None:
        return DailyDiscoveryResult(found=False)
    return DailyDiscoveryResult(
        found=True,
        discovery_id=str(discovery.id),
        selected_job_ids=[str(item.job_id) for item in discovery.selections],
        considered=discovery.considered,
        rejected=discovery.rejected,
        explanation=discovery.explanation,
        failure_sources=[item.source for item in discovery.failures],
    )
