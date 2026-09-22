from __future__ import annotations

from tests.fakes.job_source import InMemoryJobSource

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSearchQuery, JobSourceError, JobSourceErrorCode, RawJob


def _listing(source: str, external_id: str, title: str) -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title=title,
        company_name="Acme",
        location="Bengaluru",
    )


async def test_one_provider_failure_does_not_abort_others() -> None:
    healthy = InMemoryJobSource("healthy", (_listing("healthy", "1", "ML Intern"),))
    broken = InMemoryJobSource(
        "broken",
        fail_with=JobSourceError(
            "down",
            code=JobSourceErrorCode.UNAVAILABLE,
            source="broken",
            retryable=True,
        ),
    )
    use_case = SearchRegisteredSourcesUseCase(
        registry=JobSourceRegistry((healthy, broken)),
    )
    result = await use_case.execute(JobSearchQuery(keywords=("intern",)))
    assert len(result.successes) == 1
    assert result.successes[0].source.value == "healthy"
    assert len(result.failures) == 1
    assert result.failures[0].source.value == "broken"
    assert result.failures[0].error.code is JobSourceErrorCode.UNAVAILABLE


async def test_unhandled_timeout_is_normalized_per_source() -> None:
    timed_out = InMemoryJobSource("slow", fail_with=TimeoutError("late"))
    use_case = SearchRegisteredSourcesUseCase(registry=JobSourceRegistry((timed_out,)))
    result = await use_case.execute(JobSearchQuery(location="India"))
    assert result.successes == ()
    assert result.failures[0].error.code is JobSourceErrorCode.TIMEOUT
    assert result.failures[0].error.retryable is True
