from __future__ import annotations

from uuid import uuid4

from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource
from tests.fakes.repositories import InMemoryJobRepository

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import (
    SearchAndIngestJobsUseCase,
    SearchJobsCommand,
)
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSourceError, JobSourceErrorCode, RawJob


def _raw(source: str, external_id: str, title: str, **kwargs: object) -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title=title,
        company_name="Acme",
        source_url=f"https://example.com/jobs/{external_id}",
        **kwargs,  # type: ignore[arg-type]
    )


def _use_case(
    *sources: InMemoryJobSource, jobs: InMemoryJobRepository | None = None
) -> tuple[SearchAndIngestJobsUseCase, InMemoryJobRepository]:
    repository = jobs or InMemoryJobRepository()
    ingest = IngestRawJobUseCase(
        jobs=repository,
        clock=FrozenClock(),
        ids=FixedIdGenerator(*[uuid4() for _ in range(16)]),
    )
    search = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(sources)),
        ingest=ingest,
    )
    return search, repository


async def test_search_ingests_canonical_jobs() -> None:
    source = InMemoryJobSource(
        "example_board",
        (_raw("example_board", "1", "ML Intern", extra={"vendor_only": True}),),
    )
    use_case, jobs = _use_case(source)
    result = await use_case.execute(SearchJobsCommand(keywords=("intern",)))
    assert len(result.jobs) == 1
    assert result.jobs[0].title == "ML Intern"
    assert result.jobs[0].source.value == "example_board"
    stored = await jobs.get_by_source_identity(SourceKey.parse("example_board"), "1")
    assert stored is not None
    assert stored.id == result.jobs[0].id


async def test_partial_source_failure_keeps_successful_jobs() -> None:
    healthy = InMemoryJobSource("healthy", (_raw("healthy", "1", "ML Intern"),))
    broken = InMemoryJobSource(
        "broken",
        fail_with=JobSourceError(
            "down",
            code=JobSourceErrorCode.UNAVAILABLE,
            source="broken",
            retryable=True,
        ),
    )
    use_case, _jobs = _use_case(healthy, broken)
    result = await use_case.execute(SearchJobsCommand(keywords=("intern",)))
    assert len(result.jobs) == 1
    assert result.jobs[0].source.value == "healthy"
    assert result.failures[0].source.value == "broken"


async def test_duplicate_search_is_idempotent() -> None:
    source = InMemoryJobSource("example_board", (_raw("example_board", "1", "ML Intern"),))
    jobs = InMemoryJobRepository()
    use_case, _ = _use_case(source, jobs=jobs)
    first = await use_case.execute(SearchJobsCommand(keywords=("intern",)))
    second = await use_case.execute(SearchJobsCommand(keywords=("intern",)))
    assert len(first.jobs) == 1
    assert len(second.jobs) == 1
    assert first.jobs[0].id == second.jobs[0].id
    assert len(jobs._by_id) == 1
