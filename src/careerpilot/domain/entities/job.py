from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from careerpilot.domain.content_hash import job_content_hash
from careerpilot.domain.errors import InvalidJobError
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey

_MAX_TITLE = 500
_MAX_COMPANY = 255
_MAX_EXTERNAL_ID = 512
_MAX_URL = 2048
_MAX_LOCATION = 255


@dataclass(slots=True)
class Job:
    """Canonical job listing. Provider payloads must not leak into this type."""

    id: UUID
    source: SourceKey
    external_id: str
    title: str
    company_name: str
    discovered_at: datetime
    content_hash: str
    source_url: str | None = None
    application_url: str | None = None
    location: str | None = None
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    description: str | None = None
    posted_at: datetime | None = None
    extra: Mapping[str, object] = field(default_factory=dict)
    status: JobStatus = JobStatus.ACTIVE

    @classmethod
    def new(
        cls,
        *,
        job_id: UUID,
        source: SourceKey,
        external_id: str,
        title: str,
        company_name: str,
        discovered_at: datetime,
        source_url: str | None = None,
        application_url: str | None = None,
        location: str | None = None,
        remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED,
        employment_type: EmploymentType = EmploymentType.UNSPECIFIED,
        description: str | None = None,
        posted_at: datetime | None = None,
        extra: Mapping[str, object] | None = None,
        status: JobStatus = JobStatus.ACTIVE,
    ) -> Job:
        _require_aware(discovered_at, field="discovered_at")
        if posted_at is not None:
            _require_aware(posted_at, field="posted_at")

        title_n = _required_text(title, field="title", max_len=_MAX_TITLE)
        company_n = _required_text(company_name, field="company_name", max_len=_MAX_COMPANY)
        external_n = _required_text(external_id, field="external_id", max_len=_MAX_EXTERNAL_ID)
        source_url_n = _optional_url(source_url)
        application_url_n = _optional_url(application_url)
        location_n = _optional_text(location, field="location", max_len=_MAX_LOCATION)
        description_n = _optional_text(description, field="description", max_len=None)
        extra_n = dict(extra or {})

        return cls(
            id=job_id,
            source=source,
            external_id=external_n,
            title=title_n,
            company_name=company_n,
            discovered_at=discovered_at,
            content_hash=job_content_hash(
                title=title_n,
                company_name=company_n,
                description=description_n,
                source_url=source_url_n,
                application_url=application_url_n,
            ),
            source_url=source_url_n,
            application_url=application_url_n,
            location=location_n,
            remote_policy=remote_policy,
            employment_type=employment_type,
            description=description_n,
            posted_at=posted_at,
            extra=extra_n,
            status=status,
        )


def _required_text(value: str, *, field: str, max_len: int) -> str:
    trimmed = " ".join(value.split())
    if not trimmed:
        raise InvalidJobError(f"{field} is required.")
    if len(trimmed) > max_len:
        raise InvalidJobError(f"{field} must be at most {max_len} characters.")
    return trimmed


def _optional_text(value: str | None, *, field: str, max_len: int | None) -> str | None:
    if value is None:
        return None
    trimmed = " ".join(value.split())
    if not trimmed:
        return None
    if max_len is not None and len(trimmed) > max_len:
        raise InvalidJobError(f"{field} must be at most {max_len} characters.")
    return trimmed


def _optional_url(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > _MAX_URL:
        raise InvalidJobError(f"url must be at most {_MAX_URL} characters.")
    if not (trimmed.startswith("https://") or trimmed.startswith("http://")):
        raise InvalidJobError("urls must start with http:// or https://.")
    return trimmed


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidJobError(f"{field} must be timezone-aware UTC datetime.")
