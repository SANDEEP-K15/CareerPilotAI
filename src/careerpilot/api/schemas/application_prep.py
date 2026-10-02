from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApplicationPrepTalkingPointResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    point: str


class ApplicationPrepInterviewQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    focus: str


class PrepareApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID


class ApplicationPrepPackageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    job_id: UUID
    source_resume_id: UUID
    source_resume_version: int = Field(ge=1)
    guidance: str
    talking_points: tuple[ApplicationPrepTalkingPointResponse, ...]
    interview_questions: tuple[ApplicationPrepInterviewQuestionResponse, ...]
    llm_provider: str
    llm_model: str
    request_id: str
