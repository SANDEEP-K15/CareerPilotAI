from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeTailoringChangeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    description: str


class TailorResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID


class ResumeTailoringResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    job_id: UUID
    source_resume_id: UUID
    source_resume_version: int = Field(ge=1)
    tailored_content: str
    changes: tuple[ResumeTailoringChangeResponse, ...]
    llm_provider: str
    llm_model: str
    request_id: str
