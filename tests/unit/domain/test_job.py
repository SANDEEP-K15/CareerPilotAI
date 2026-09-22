from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from careerpilot.domain.content_hash import job_content_hash
from careerpilot.domain.entities.job import Job
from careerpilot.domain.errors import InvalidJobError
from careerpilot.domain.value_objects.source_key import SourceKey


def _job(
    *,
    title: str = "ML Intern",
    discovered_at: datetime | None = None,
    source: SourceKey | None = None,
    source_url: str | None = None,
    extra: dict[str, object] | None = None,
) -> Job:
    return Job.new(
        job_id=uuid4(),
        source=source or SourceKey.parse("example_board"),
        external_id="abc-123",
        title=title,
        company_name="Acme",
        discovered_at=discovered_at or datetime(2026, 9, 22, tzinfo=UTC),
        source_url=source_url,
        extra=extra,
    )


def test_source_key_normalizes_and_rejects_invalid_raw_value() -> None:
    assert SourceKey.parse("Example-Board").value == "example_board"
    with pytest.raises(InvalidJobError):
        SourceKey(value="Adzuna")


def test_job_requires_title() -> None:
    with pytest.raises(InvalidJobError) as exc:
        _job(title="  ")
    assert exc.value.code == "invalid_job"


def test_job_rejects_naive_datetime() -> None:
    with pytest.raises(InvalidJobError):
        _job(discovered_at=datetime(2026, 9, 22))


def test_job_rejects_non_http_url() -> None:
    with pytest.raises(InvalidJobError):
        _job(source_url="ftp://example.com/job")


def test_content_hash_is_stable_and_case_insensitive_on_title() -> None:
    first = job_content_hash(
        title="ML Intern",
        company_name="Acme",
        description=None,
        source_url=None,
        application_url=None,
    )
    second = job_content_hash(
        title="ml intern",
        company_name="ACME",
        description=None,
        source_url=None,
        application_url=None,
    )
    assert first == second
    assert len(first) == 64


def test_job_new_sets_content_hash() -> None:
    job = _job()
    assert job.content_hash == job_content_hash(
        title=job.title,
        company_name=job.company_name,
        description=job.description,
        source_url=job.source_url,
        application_url=job.application_url,
    )


def test_job_does_not_encode_a_specific_provider() -> None:
    job = _job(source=SourceKey.parse("any_source"), extra={"raw_id": "1"})
    assert job.source.value == "any_source"
    assert "adzuna" not in job.source.value
