"""Provider-neutral job source contracts.

Adapters implement ``JobSourcePort``. Vendor SDKs and provider DTOs stay in
infrastructure modules that do not exist until a later milestone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from careerpilot.domain.value_objects.source_key import SourceKey

_MAX_PAGE_SIZE = 50
_MAX_KEYWORD_LEN = 200
_MAX_LOCATION_LEN = 255


class JobSourceErrorCode(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    MALFORMED_RESPONSE = "malformed_response"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


class JobSourceError(Exception):
    """Normalized adapter failure. Never wrap a vendor exception type."""

    def __init__(
        self,
        message: str,
        *,
        code: JobSourceErrorCode,
        source: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.source = source
        self.retryable = retryable


class InvalidJobSearchQueryError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = "invalid_job_search_query"


def normalize_job_source_failure(source: str, exc: BaseException) -> JobSourceError:
    """Map generic I/O failures to JobSourceError. Idempotent for JobSourceError."""
    if isinstance(exc, JobSourceError):
        return exc
    if isinstance(exc, TimeoutError):
        return JobSourceError(
            "Job source timed out.",
            code=JobSourceErrorCode.TIMEOUT,
            source=source,
            retryable=True,
        )
    if isinstance(exc, ConnectionError | OSError):
        return JobSourceError(
            "Job source is unavailable.",
            code=JobSourceErrorCode.UNAVAILABLE,
            source=source,
            retryable=True,
        )
    return JobSourceError(
        "Job source failed.",
        code=JobSourceErrorCode.UNKNOWN,
        source=source,
        retryable=False,
    )


@dataclass(frozen=True, slots=True)
class JobSourceCapabilities:
    supports_search: bool = True
    supports_pagination: bool = True
    requires_credentials: bool = False


@dataclass(frozen=True, slots=True)
class JobSearchQuery:
    keywords: tuple[str, ...] = ()
    location: str | None = None
    remote_only: bool | None = None
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        keywords = tuple(part for raw in self.keywords if (part := " ".join(raw.split())))
        if any(len(part) > _MAX_KEYWORD_LEN for part in keywords):
            raise InvalidJobSearchQueryError(
                f"each keyword must be at most {_MAX_KEYWORD_LEN} characters."
            )
        object.__setattr__(self, "keywords", keywords)

        location = self.location
        if location is not None:
            location = " ".join(location.split()) or None
            if location is not None and len(location) > _MAX_LOCATION_LEN:
                raise InvalidJobSearchQueryError(
                    f"location must be at most {_MAX_LOCATION_LEN} characters."
                )
            object.__setattr__(self, "location", location)

        if not self.keywords and self.location is None:
            raise InvalidJobSearchQueryError("at least one keyword or a location is required.")
        if self.page < 1:
            raise InvalidJobSearchQueryError("page must be >= 1.")
        if not 1 <= self.page_size <= _MAX_PAGE_SIZE:
            raise InvalidJobSearchQueryError(f"page_size must be between 1 and {_MAX_PAGE_SIZE}.")


@dataclass(frozen=True, slots=True)
class RawJob:
    """Provider-neutral listing. Not a persisted canonical Job."""

    source: SourceKey
    external_id: str
    title: str
    company_name: str
    source_url: str | None = None
    application_url: str | None = None
    location: str | None = None
    description: str | None = None
    posted_at: datetime | None = None
    extra: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class JobSearchPage:
    items: tuple[RawJob, ...]
    page: int
    page_size: int
    has_more: bool


class JobSourcePort(Protocol):
    @property
    def source_key(self) -> SourceKey: ...

    @property
    def capabilities(self) -> JobSourceCapabilities: ...

    async def search(self, query: JobSearchQuery) -> JobSearchPage:
        """Return one page of listings or raise JobSourceError."""
        ...
