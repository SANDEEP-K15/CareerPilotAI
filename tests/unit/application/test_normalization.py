from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from careerpilot.application.jobs.normalization import job_from_raw
from careerpilot.domain.content_hash import job_content_hash
from careerpilot.domain.errors import InvalidJobError
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import RawJob


def _raw(**overrides: object) -> RawJob:
    payload: dict[str, object] = {
        "source": SourceKey.parse("example_board"),
        "external_id": "ext-1",
        "title": "ML Intern",
        "company_name": "Acme",
        "source_url": "https://example.com/jobs/1",
        "application_url": "https://apply.example.com/1",
        "location": "London",
        "description": "Build things.",
        "posted_at": datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
        "extra": {"note": "opaque"},
    }
    payload.update(overrides)
    return RawJob(**payload)  # type: ignore[arg-type]


def test_maps_raw_job_to_canonical_job() -> None:
    job_id = uuid4()
    discovered = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
    job = job_from_raw(_raw(), job_id=job_id, discovered_at=discovered)
    assert job.id == job_id
    assert job.source.value == "example_board"
    assert job.external_id == "ext-1"
    assert job.title == "ML Intern"
    assert job.company_name == "Acme"
    assert job.source_url == "https://example.com/jobs/1"
    assert job.application_url == "https://apply.example.com/1"
    assert job.location == "London"
    assert job.description == "Build things."
    assert job.posted_at == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    assert job.discovered_at == discovered
    assert job.extra == {"note": "opaque"}
    assert job.content_hash == job_content_hash(
        title=job.title,
        company_name=job.company_name,
        description=job.description,
        source_url=job.source_url,
        application_url=job.application_url,
    )


def test_missing_optional_fields_are_none() -> None:
    job = job_from_raw(
        RawJob(
            source=SourceKey.parse("example_board"),
            external_id="ext-2",
            title="Engineer",
            company_name="Acme",
        ),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.source_url is None
    assert job.application_url is None
    assert job.location is None
    assert job.description is None
    assert job.posted_at is None
    assert dict(job.extra) == {}


def test_missing_required_title_is_invalid() -> None:
    with pytest.raises(InvalidJobError):
        job_from_raw(
            _raw(title="  "),
            job_id=uuid4(),
            discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_missing_required_external_id_is_invalid() -> None:
    with pytest.raises(InvalidJobError):
        job_from_raw(
            _raw(external_id=""),
            job_id=uuid4(),
            discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_naive_posted_at_is_treated_as_utc() -> None:
    job = job_from_raw(
        _raw(posted_at=datetime(2026, 9, 1, 12, 0)),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.posted_at == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_offset_posted_at_converts_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    job = job_from_raw(
        _raw(posted_at=datetime(2026, 9, 1, 17, 30, tzinfo=ist)),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.posted_at == datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def test_urls_are_canonicalized_without_dropping_query() -> None:
    job = job_from_raw(
        _raw(
            source_url="HTTPS://Example.COM/jobs/1?ref=src#frag",
            application_url="https://APPLY.example.com/1?token=abc#top",
        ),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.source_url == "https://example.com/jobs/1?ref=src"
    assert job.application_url == "https://apply.example.com/1?token=abc"


def test_blank_url_is_missing_not_invented() -> None:
    job = job_from_raw(
        _raw(source_url="  ", application_url=None),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.source_url is None
    assert job.application_url is None


def test_non_http_url_is_invalid() -> None:
    with pytest.raises(InvalidJobError):
        job_from_raw(
            _raw(source_url="ftp://example.com/job"),
            job_id=uuid4(),
            discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_content_hash_is_stable_for_equivalent_normalized_input() -> None:
    discovered = datetime(2026, 9, 22, tzinfo=UTC)
    first = job_from_raw(
        _raw(title="  ML   Intern ", company_name="ACME"),
        job_id=uuid4(),
        discovered_at=discovered,
    )
    second = job_from_raw(
        _raw(title="ml intern", company_name="acme"),
        job_id=uuid4(),
        discovered_at=discovered,
    )
    assert first.content_hash == second.content_hash
    assert first.content_hash == job_content_hash(
        title="ML Intern",
        company_name="Acme",
        description="Build things.",
        source_url="https://example.com/jobs/1",
        application_url="https://apply.example.com/1",
    )


def test_whitespace_only_optional_text_is_none() -> None:
    job = job_from_raw(
        _raw(location="   ", description="  \n  "),
        job_id=uuid4(),
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
    )
    assert job.location is None
    assert job.description is None
