from __future__ import annotations

from dataclasses import dataclass

from careerpilot.application.use_cases.approval_requests import (
    ApproveApprovalRequestUseCase,
    CreateApprovalRequestUseCase,
    GetApprovalRequestUseCase,
    ListApprovalRequestsUseCase,
    RejectApprovalRequestUseCase,
)


@dataclass(frozen=True, slots=True)
class ApprovalApi:
    create_request: CreateApprovalRequestUseCase
    get_request: GetApprovalRequestUseCase
    list_requests: ListApprovalRequestsUseCase
    approve_request: ApproveApprovalRequestUseCase
    reject_request: RejectApprovalRequestUseCase
