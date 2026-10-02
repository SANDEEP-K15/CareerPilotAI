from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from careerpilot.api.deps_approvals import ApprovalApi
from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters import (
    approval_request_list_to_response,
    approval_request_to_response,
)
from careerpilot.api.schemas.approval_requests import (
    ApprovalDecisionBody,
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
    CreateApprovalRequestBody,
)
from careerpilot.application.errors import ApplicationError
from careerpilot.domain.value_objects.approval_status import ApprovalStatus

router = APIRouter()


def _approval_api(request: Request) -> ApprovalApi:
    api = getattr(request.app.state, "approval_api", None)
    if not isinstance(api, ApprovalApi):
        raise ApplicationError("Approval API is not configured.", code="not_configured")
    return api


@router.post(
    "/users/{user_id}/approval-requests",
    response_model=ApprovalRequestResponse,
)
async def create_approval_request(
    user_id: UUID,
    payload: CreateApprovalRequestBody,
    request: Request,
) -> ApprovalRequestResponse:
    request_id = request_id_of(request)
    created = await _approval_api(request).create_request.execute(
        user_id=user_id,
        job_id=payload.job_id,
        action=payload.action,
        reason=payload.reason,
        expires_at=payload.expires_at,
    )
    return approval_request_to_response(created, request_id=request_id)


@router.get(
    "/users/{user_id}/approval-requests",
    response_model=ApprovalRequestListResponse,
)
async def list_approval_requests(
    user_id: UUID,
    request: Request,
    status: ApprovalStatus | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> ApprovalRequestListResponse:
    request_id = request_id_of(request)
    items = await _approval_api(request).list_requests.execute(
        user_id,
        status=status,
        limit=limit,
    )
    return approval_request_list_to_response(items, request_id=request_id)


@router.get(
    "/users/{user_id}/approval-requests/{approval_request_id}",
    response_model=ApprovalRequestResponse,
)
async def get_approval_request(
    user_id: UUID,
    approval_request_id: UUID,
    request: Request,
) -> ApprovalRequestResponse:
    request_id = request_id_of(request)
    item = await _approval_api(request).get_request.execute(user_id, approval_request_id)
    return approval_request_to_response(item, request_id=request_id)


@router.post(
    "/users/{user_id}/approval-requests/{approval_request_id}/approve",
    response_model=ApprovalRequestResponse,
)
async def approve_approval_request(
    user_id: UUID,
    approval_request_id: UUID,
    payload: ApprovalDecisionBody,
    request: Request,
) -> ApprovalRequestResponse:
    request_id = request_id_of(request)
    item = await _approval_api(request).approve_request.execute(
        user_id,
        approval_request_id,
        decision_note=payload.decision_note,
    )
    return approval_request_to_response(item, request_id=request_id)


@router.post(
    "/users/{user_id}/approval-requests/{approval_request_id}/reject",
    response_model=ApprovalRequestResponse,
)
async def reject_approval_request(
    user_id: UUID,
    approval_request_id: UUID,
    payload: ApprovalDecisionBody,
    request: Request,
) -> ApprovalRequestResponse:
    request_id = request_id_of(request)
    item = await _approval_api(request).reject_request.execute(
        user_id,
        approval_request_id,
        decision_note=payload.decision_note,
    )
    return approval_request_to_response(item, request_id=request_id)
