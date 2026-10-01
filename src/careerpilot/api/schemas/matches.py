from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    score: int
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    reasons: tuple[str, ...]
    concerns: tuple[str, ...]


class MatchReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    profile_id: UUID
    threshold: int
    considered: int
    rejected: int
    items: tuple[JobMatchResponse, ...]
    request_id: str
