from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClientTaskSubmitRequest(BaseModel):
    """External client task submission (e.g. Hermes → CareerPilot)."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    intent: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None


class ClientTaskErrorResponse(BaseModel):
    code: str
    message: str


class ClientTaskStepResponse(BaseModel):
    step_id: str
    agent: str
    status: str
    error_code: str | None = None
    error_message: str | None = None


class ClientTaskSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    correlation_id: str | None
    status: str
    plan_id: str
    summary: str
    steps: tuple[ClientTaskStepResponse, ...]
    output: dict[str, Any] | None = None
    error: ClientTaskErrorResponse | None = None
