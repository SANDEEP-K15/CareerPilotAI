from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from careerpilot.domain.value_objects.approval_action import ApprovalAction


class CreateApprovalRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    action: ApprovalAction
    reason: str | None = None
    expires_at: datetime | None = None


class ApprovalDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_note: str | None = None


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    job_id: UUID
    action: str
    status: str
    reason: str | None
    decision_note: str | None
    expires_at: datetime
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime
    request_id: str


class ApprovalRequestListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: tuple[ApprovalRequestResponse, ...]
    request_id: str
