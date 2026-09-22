"""JobSourcePort contract tests against the in-memory fake.

Real HTTP adapters are added in later milestones and must satisfy the same
behaviors: search, empty pages, pagination, and JobSourceError on failure.
"""

from __future__ import annotations

import pytest

from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import (
    JobSearchQuery,
    JobSourceError,
    JobSourceErrorCode,
    RawJob,
)
from tests.fakes.job_source import InMemoryJobSource


def _listing(*, external_id: str, title: str, location: str | None = "India") -> RawJob:
    return RawJob(
        source=SourceKey.parse("memory"),
        external_id=external_id,
        title=title,
        company_name="Acme",
        location=location,
        source_url=f"https://example.com/jobs/{external_id}",
    )


def _source(
    listings: tuple[RawJob, ...] = (),
    fail_with: BaseException | None = None,
) -> InMemoryJobSource:
    return InMemoryJobSource("memory", listings, fail_with=fail_with)


async def test_successful_search() -> None:
    source = _source(
        (
            _listing(external_id="1", title="ML Intern"),
            _listing(external_id="2", title="Data Analyst"),
        )
    )
    page = await source.search(JobSearchQuery(keywords=("intern",)))
    assert source.capabilities.supports_search is True
    assert [item.external_id for item in page.items] == ["1"]
    assert page.has_more is False


async def test_empty_results() -> None:
    source = _source((_listing(external_id="1", title="Backend Engineer"),))
    page = await source.search(JobSearchQuery(keywords=("intern",), location="India"))
    assert page.items == ()
    assert page.has_more is False


async def test_pagination() -> None:
    listings = tuple(
        _listing(external_id=str(index), title=f"ML Intern {index}") for index in range(5)
    )
    source = _source(listings)
    page = await source.search(JobSearchQuery(keywords=("intern",), page=2, page_size=2))
    assert [item.external_id for item in page.items] == ["2", "3"]
    assert page.page == 2
    assert page.page_size == 2
    assert page.has_more is True
    last = await source.search(JobSearchQuery(keywords=("intern",), page=3, page_size=2))
    assert [item.external_id for item in last.items] == ["4"]
    assert last.has_more is False


async def test_provider_failure() -> None:
    source = _source(
        fail_with=JobSourceError(
            "unavailable",
            code=JobSourceErrorCode.UNAVAILABLE,
            source="memory",
            retryable=True,
        )
    )
    with pytest.raises(JobSourceError) as exc:
        await source.search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.UNAVAILABLE
    assert exc.value.retryable is True


async def test_timeout_failure() -> None:
    source = _source(fail_with=TimeoutError("late"))
    with pytest.raises(TimeoutError):
        await source.search(JobSearchQuery(location="India"))
