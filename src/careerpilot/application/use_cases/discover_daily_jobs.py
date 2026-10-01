from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from careerpilot.application.errors import ApplicationError, CareerProfileNotFoundError
from careerpilot.application.use_cases.search_and_ingest_jobs import (
    SearchAndIngestJobsUseCase,
    SearchJobsCommand,
)
from careerpilot.domain.discovery import (
    DAILY_SELECTION_LIMIT,
    explain_discovery,
    select_daily_jobs,
)
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.daily_discovery import (
    DailyDiscovery,
    DiscoverySourceFailure,
)
from careerpilot.domain.entities.job import Job
from careerpilot.domain.matching import DEFAULT_THRESHOLD
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import (
    CareerProfileRepository,
    DailyDiscoveryRepository,
    JobRepository,
)

DISCOVERY_PAGE_SIZE = 50


class InvalidDiscoveryQueryError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_discovery_query")


@dataclass(frozen=True, slots=True)
class DiscoverDailyJobsCommand:
    user_id: UUID
    run_on: date
    threshold: int = DEFAULT_THRESHOLD
    limit: int = DAILY_SELECTION_LIMIT


class DiscoverDailyJobsUseCase:
    """Search, ingest, match, and store one daily discovery. Does not call Temporal."""

    def __init__(
        self,
        *,
        profiles: CareerProfileRepository,
        jobs: JobRepository,
        discoveries: DailyDiscoveryRepository,
        search: SearchAndIngestJobsUseCase,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs
        self._discoveries = discoveries
        self._search = search
        self._clock = clock
        self._ids = ids

    async def execute(self, command: DiscoverDailyJobsCommand) -> DailyDiscovery:
        self._validate(command.threshold, command.limit)
        existing = await self.find_existing(command.user_id, command.run_on)
        if existing is not None:
            return existing
        profile = await self.load_profile(command.user_id)
        searchable = profile_is_searchable(profile)
        if searchable:
            job_ids, failures = await self.search_and_ingest(profile)
        else:
            job_ids, failures = (), ()
        return await self.rank_and_persist(
            user_id=command.user_id,
            run_on=command.run_on,
            threshold=command.threshold,
            limit=command.limit,
            searchable=searchable,
            job_ids=job_ids,
            failures=failures,
        )

    async def find_existing(self, user_id: UUID, run_on: date) -> DailyDiscovery | None:
        return await self._discoveries.get_by_user_and_run(user_id, run_on)

    async def load_profile(self, user_id: UUID) -> CareerProfile:
        profile = await self._profiles.get_by_user_id(user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(user_id))
        return profile

    async def search_and_ingest(
        self, profile: CareerProfile
    ) -> tuple[tuple[UUID, ...], tuple[DiscoverySourceFailure, ...]]:
        keywords, location = search_terms(profile)
        result = await self._search.execute(
            SearchJobsCommand(
                keywords=keywords,
                location=location,
                remote_only=True if profile.remote_policy is RemotePolicy.REMOTE else None,
                page=1,
                page_size=DISCOVERY_PAGE_SIZE,
            )
        )
        failures = tuple(
            DiscoverySourceFailure(
                source=item.source.value,
                code=item.error.code.value,
                message=item.error.message,
            )
            for item in result.failures
        )
        return tuple(job.id for job in result.jobs), failures

    async def rank_and_persist(
        self,
        *,
        user_id: UUID,
        run_on: date,
        threshold: int,
        limit: int,
        searchable: bool,
        job_ids: tuple[UUID, ...],
        failures: tuple[DiscoverySourceFailure, ...],
    ) -> DailyDiscovery:
        self._validate(threshold, limit)
        existing = await self.find_existing(user_id, run_on)
        if existing is not None:
            return existing
        profile = await self.load_profile(user_id)
        if searchable:
            loaded = await self._load_jobs(job_ids)
            chosen = select_daily_jobs(profile, loaded, threshold=threshold, limit=limit)
        else:
            chosen = select_daily_jobs(profile, (), threshold=threshold, limit=limit)
        now = self._clock.now()
        discovery = DailyDiscovery(
            id=self._ids.new_id(),
            user_id=user_id,
            profile_id=profile.id,
            run_on=run_on,
            threshold=threshold,
            limit=limit,
            considered=chosen.considered,
            rejected=chosen.rejected,
            selections=chosen.selections,
            failures=failures,
            explanation=explain_discovery(
                searchable=searchable,
                selected=len(chosen.selections),
                limit=limit,
                considered=chosen.considered,
                failure_count=len(failures),
            ),
            created_at=now,
            updated_at=now,
        )
        return await self._discoveries.save(discovery)

    async def _load_jobs(self, job_ids: tuple[UUID, ...]) -> tuple[Job, ...]:
        loaded: list[Job] = []
        seen: set[UUID] = set()
        for job_id in job_ids:
            if job_id in seen:
                continue
            seen.add(job_id)
            job = await self._jobs.get_by_id(job_id)
            if job is not None:
                loaded.append(job)
        return tuple(loaded)

    @staticmethod
    def _validate(threshold: int, limit: int) -> None:
        if not 0 <= threshold <= 100:
            raise InvalidDiscoveryQueryError("threshold must be between 0 and 100.")
        if not 1 <= limit <= DAILY_SELECTION_LIMIT:
            raise InvalidDiscoveryQueryError(
                f"limit must be between 1 and {DAILY_SELECTION_LIMIT}."
            )


def profile_is_searchable(profile: CareerProfile) -> bool:
    keywords, location = search_terms(profile)
    return bool(keywords) or location is not None


def search_terms(profile: CareerProfile) -> tuple[tuple[str, ...], str | None]:
    keywords = profile.target_titles
    if not keywords and profile.headline:
        keywords = (profile.headline,)
    location = profile.locations[0] if profile.locations else None
    return keywords, location
