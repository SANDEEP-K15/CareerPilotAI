from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobSearchRequest(BaseModel):
    """HTTP body for POST /api/v1/jobs/search. Mirrors JobSearchQuery plus sources."""

    model_config = ConfigDict(extra="forbid")

    keywords: tuple[str, ...] = ()
    location: str | None = None
    remote_only: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
    sources: tuple[str, ...] | None = None


class JobResponse(BaseModel):
    """Canonical Job DTO. Not a RawJob and not an ORM model."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    source: str
    external_id: str
    title: str
    company_name: str
    source_url: str | None
    application_url: str | None
    location: str | None
    remote_policy: str
    employment_type: str
    description: str | None
    posted_at: datetime | None
    discovered_at: datetime
    content_hash: str
    status: str


class SourcePageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    page: int
    page_size: int
    returned: int
    has_more: bool


class SourceErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    code: str
    message: str
    retryable: bool


class JobSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[JobResponse, ...]
    page: int
    page_size: int
    has_more: bool
    sources: tuple[SourcePageResponse, ...]
    errors: tuple[SourceErrorResponse, ...]
    request_id: str
