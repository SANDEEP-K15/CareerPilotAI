from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource
from tests.fakes.repositories import (
    InMemoryCareerProfileRepository,
    InMemoryDailyDiscoveryRepository,
    InMemoryJobRepository,
)

from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.discover_daily_jobs import (
    DiscoverDailyJobsCommand,
    DiscoverDailyJobsUseCase,
    InvalidDiscoveryQueryError,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import (
    JobSearchPage,
    JobSearchQuery,
    JobSourceError,
    JobSourceErrorCode,
    RawJob,
)

RUN_ON = date(2026, 10, 1)


class CountingSource(InMemoryJobSource):
    def __init__(self, source: str, listings: tuple[RawJob, ...] = (), **kwargs: object) -> None:
        super().__init__(source, listings, **kwargs)  # type: ignore[arg-type]
        self.calls = 0

    async def search(self, query: JobSearchQuery) -> JobSearchPage:
        self.calls += 1
        return await super().search(query)


def _raw(source: str, external_id: str, *, description: str = "Python and SQL.") -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title="ML Intern",
        company_name="Acme",
        location="London",
        description=description,
    )


def _profile(user_id: UUID, **overrides: object) -> CareerProfile:
    payload: dict[str, object] = {
        "profile_id": uuid4(),
        "user_id": user_id,
        "now": datetime(2026, 10, 1, tzinfo=UTC),
        "skills": ("Python", "SQL"),
        "target_titles": ("ML Intern",),
        "locations": ("London",),
        "remote_policy": RemotePolicy.UNSPECIFIED,
        "employment_type": EmploymentType.UNSPECIFIED,
    }
    payload.update(overrides)
    return CareerProfile.new(**payload)  # type: ignore[arg-type]


def _wire(
    sources: tuple[CountingSource, ...],
    *,
    ids: tuple[UUID, ...] = (),
) -> tuple[DiscoverDailyJobsUseCase, InMemoryCareerProfileRepository, InMemoryJobRepository]:
    jobs = InMemoryJobRepository()
    profiles = InMemoryCareerProfileRepository()
    generator = FixedIdGenerator(*ids) if ids else FixedIdGenerator()
    use_case = DiscoverDailyJobsUseCase(
        profiles=profiles,
        jobs=jobs,
        discoveries=InMemoryDailyDiscoveryRepository(),
        search=SearchAndIngestJobsUseCase(
            search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(sources)),
            ingest=IngestRawJobUseCase(jobs=jobs, clock=FrozenClock(), ids=generator),
        ),
        clock=FrozenClock(),
        ids=generator,
    )
    return use_case, profiles, jobs


async def test_positive_discovery_ranks_and_explains() -> None:
    strong_id, partial_id, discovery_id = uuid4(), uuid4(), uuid4()
    source = CountingSource(
        "alpha",
        (
            _raw("alpha", "strong"),
            _raw("alpha", "partial", description="Python intern role."),
        ),
    )
    use_case, profiles, _jobs = _wire((source,), ids=(strong_id, partial_id, discovery_id))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    result = await use_case.execute(DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON))
    assert result.id == discovery_id
    assert [item.job_id for item in result.selections] == [strong_id, partial_id]
    assert result.selections[0].score > result.selections[1].score
    assert result.selections[1].missing_skills == ("SQL",)
    assert result.considered == 2
    assert result.rejected == 0
    assert result.explanation == (
        "2 sufficiently relevant jobs; fewer than 20 met the threshold."
    )


async def test_selects_at_most_20_without_padding() -> None:
    job_ids = [uuid4() for _ in range(21)]
    discovery_id = uuid4()
    source = CountingSource("alpha", tuple(_raw("alpha", str(index)) for index in range(21)))
    use_case, profiles, jobs = _wire((source,), ids=(*job_ids, discovery_id))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    unrelated = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("other_board"),
        external_id="catalog-only",
        title="ML Intern",
        company_name="Acme",
        discovered_at=datetime(2026, 10, 1, tzinfo=UTC),
        description="Python and SQL.",
        location="London",
    )
    await jobs.add(unrelated)
    result = await use_case.execute(DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON))
    expected = sorted(job_ids, key=str)[:20]
    assert [item.job_id for item in result.selections] == expected
    assert unrelated.id not in {item.job_id for item in result.selections}
    assert result.considered == 21
    assert result.rejected == 0
    assert len(result.selections) == 20
    assert result.explanation == "20 sufficiently relevant jobs."


async def test_threshold_drops_weak_jobs_instead_of_padding() -> None:
    job_id, discovery_id = uuid4(), uuid4()
    source = CountingSource("alpha", (_raw("alpha", "one"),))
    use_case, profiles, _jobs = _wire((source,), ids=(job_id, discovery_id))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    result = await use_case.execute(
        DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON, threshold=95)
    )
    assert result.selections == ()
    assert result.considered == 1
    assert result.rejected == 1
    assert result.explanation == "No jobs met the relevance threshold."


async def test_multiple_sources_and_isolated_provider_failure() -> None:
    alpha_id, beta_id, discovery_id = uuid4(), uuid4(), uuid4()
    alpha = CountingSource("alpha", (_raw("alpha", "a"),))
    beta = CountingSource(
        "beta",
        (),
        fail_with=JobSourceError(
            "Job source timed out.",
            code=JobSourceErrorCode.TIMEOUT,
            source="beta",
            retryable=True,
        ),
    )
    gamma = CountingSource("gamma", (_raw("gamma", "g"),))
    use_case, profiles, _jobs = _wire(
        (gamma, alpha, beta), ids=(alpha_id, beta_id, discovery_id)
    )
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    result = await use_case.execute(DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON))
    assert {item.job_id for item in result.selections} == {alpha_id, beta_id}
    assert [(item.source, item.code) for item in result.failures] == [("beta", "timeout")]
    assert "secret" not in result.explanation


async def test_provider_exception_text_is_not_stored() -> None:
    discovery_id = uuid4()
    source = CountingSource(
        "alpha", fail_with=RuntimeError("secret-token-must-not-leak")
    )
    use_case, profiles, _jobs = _wire((source,), ids=(discovery_id,))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    result = await use_case.execute(DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON))
    assert result.selections == ()
    assert result.failures[0].message == "Job source failed."
    assert "secret-token" not in result.failures[0].message
    assert result.explanation == "No jobs ingested; one or more sources failed."


async def test_empty_sources_and_unsearchable_profile() -> None:
    discovery_id = uuid4()
    source = CountingSource("alpha", ())
    use_case, profiles, _jobs = _wire((source,), ids=(discovery_id,))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    empty = await use_case.execute(DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON))
    assert empty.selections == ()
    assert empty.explanation == "No jobs returned from registered sources."
    assert source.calls == 1

    bare = uuid4()
    await profiles.add(
        _profile(bare, skills=(), target_titles=(), locations=(), headline=None)
    )
    quiet = CountingSource("alpha", (_raw("alpha", "ignored"),))
    other, other_profiles, _jobs = _wire((quiet,), ids=(uuid4(),))
    await other_profiles.add(
        _profile(bare, skills=(), target_titles=(), locations=(), headline=None)
    )
    result = await other.execute(DiscoverDailyJobsCommand(user_id=bare, run_on=RUN_ON))
    assert quiet.calls == 0
    assert result.selections == ()
    assert result.explanation == "Profile has no target titles or locations to search."


async def test_rerun_is_idempotent() -> None:
    job_id, discovery_id = uuid4(), uuid4()
    source = CountingSource("alpha", (_raw("alpha", "a"),))
    use_case, profiles, jobs = _wire((source,), ids=(job_id, discovery_id))
    user_id = uuid4()
    await profiles.add(_profile(user_id))
    command = DiscoverDailyJobsCommand(user_id=user_id, run_on=RUN_ON)
    first = await use_case.execute(command)
    second = await use_case.execute(command)
    assert first == second
    assert source.calls == 1
    assert len(await jobs.list_active()) == 1


async def test_missing_profile_and_invalid_query() -> None:
    use_case, _profiles, _jobs = _wire(())
    with pytest.raises(CareerProfileNotFoundError):
        await use_case.execute(DiscoverDailyJobsCommand(user_id=uuid4(), run_on=RUN_ON))
    with pytest.raises(InvalidDiscoveryQueryError):
        await use_case.execute(
            DiscoverDailyJobsCommand(user_id=uuid4(), run_on=RUN_ON, threshold=101)
        )
    with pytest.raises(InvalidDiscoveryQueryError):
        await use_case.execute(
            DiscoverDailyJobsCommand(user_id=uuid4(), run_on=RUN_ON, limit=21)
        )
