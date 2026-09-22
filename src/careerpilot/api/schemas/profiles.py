from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy


class CareerProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str | None = None
    summary: str | None = None
    skills: tuple[str, ...] = ()
    target_titles: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    years_experience: int | None = Field(default=None, ge=0, le=60)


class CareerProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    headline: str | None
    summary: str | None
    skills: tuple[str, ...]
    target_titles: tuple[str, ...]
    locations: tuple[str, ...]
    remote_policy: str
    employment_type: str
    years_experience: int | None
    created_at: datetime
    updated_at: datetime


class ResumeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    label: str | None = None


class ResumeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    version: int
    label: str | None
    content: str
    content_type: str
    is_active: bool
    created_at: datetime


class ResumeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[ResumeResponse, ...]
