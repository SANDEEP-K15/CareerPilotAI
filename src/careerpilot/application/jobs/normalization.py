"""Provider-neutral RawJob → canonical Job mapping."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from careerpilot.domain.entities.job import Job
from careerpilot.ports.job_source import RawJob


def job_from_raw(
    raw: RawJob,
    *,
    job_id: UUID,
    discovered_at: datetime,
) -> Job:
    """Build a canonical Job. Does not persist.

    Raises InvalidJobError if required data is missing.
    """
    return Job.new(
        job_id=job_id,
        source=raw.source,
        external_id=raw.external_id,
        title=raw.title,
        company_name=raw.company_name,
        discovered_at=discovered_at,
        source_url=raw.source_url,
        application_url=raw.application_url,
        location=raw.location,
        description=raw.description,
        posted_at=_as_utc(raw.posted_at),
        extra=_copy_extra(raw.extra),
    )


def jobs_are_equivalent(left: Job, right: Job) -> bool:
    return (
        left.source == right.source
        and left.external_id == right.external_id
        and left.content_hash == right.content_hash
        and left.title == right.title
        and left.company_name == right.company_name
        and left.source_url == right.source_url
        and left.application_url == right.application_url
        and left.location == right.location
        and left.description == right.description
        and left.posted_at == right.posted_at
        and dict(left.extra) == dict(right.extra)
        and left.status == right.status
        and left.remote_policy == right.remote_policy
        and left.employment_type == right.employment_type
    )


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _copy_extra(extra: Mapping[str, object]) -> dict[str, object]:
    return dict(extra)
