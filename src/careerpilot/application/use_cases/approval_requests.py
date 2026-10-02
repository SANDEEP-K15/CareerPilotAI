from __future__ import annotations

from datetime import datetime
from uuid import UUID

from careerpilot.application.errors import (
    ApprovalRequestNotFoundError,
    DuplicatePendingApprovalError,
    InvalidApprovalTransitionError,
    JobNotFoundError,
    UserNotFoundError,
)
from careerpilot.domain.entities.approval_request import DEFAULT_APPROVAL_TTL, ApprovalRequest
from careerpilot.domain.errors import InvalidApprovalRequestError
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import ApprovalRequestRepository, JobRepository, UserRepository


async def _synchronize_expiration(
    *,
    repository: ApprovalRequestRepository,
    request: ApprovalRequest,
    now: datetime,
) -> ApprovalRequest:
    if request.status is ApprovalStatus.PENDING and now >= request.expires_at:
        expired = request.mark_expired(now)
        await repository.update(expired)
        return expired
    return request


class CreateApprovalRequestUseCase:
    def __init__(
        self,
        *,
        users: UserRepository,
        jobs: JobRepository,
        approvals: ApprovalRequestRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._users = users
        self._jobs = jobs
        self._approvals = approvals
        self._clock = clock
        self._ids = ids

    async def execute(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        action: ApprovalAction,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> ApprovalRequest:
        if await self._users.get_by_id(user_id) is None:
            raise UserNotFoundError(str(user_id))
        if await self._jobs.get_by_id(job_id) is None:
            raise JobNotFoundError(str(job_id))
        now = self._clock.now()
        expiry = expires_at or (now + DEFAULT_APPROVAL_TTL)
        try:
            request = ApprovalRequest.new(
                request_id=self._ids.new_id(),
                user_id=user_id,
                job_id=job_id,
                action=action,
                created_at=now,
                expires_at=expiry,
                reason=reason,
            )
        except InvalidApprovalRequestError as exc:
            raise InvalidApprovalTransitionError(str(exc.message)) from exc
        pending = await self._approvals.list_pending_for(user_id, job_id, action)
        for existing in pending:
            current = await _synchronize_expiration(
                repository=self._approvals,
                request=existing,
                now=now,
            )
            if current.effective_status(now) is ApprovalStatus.PENDING:
                raise DuplicatePendingApprovalError(str(user_id), str(job_id), action.value)
        await self._approvals.add(request)
        return request


class GetApprovalRequestUseCase:
    def __init__(
        self,
        *,
        approvals: ApprovalRequestRepository,
        clock: ClockPort,
    ) -> None:
        self._approvals = approvals
        self._clock = clock

    async def execute(self, user_id: UUID, request_id: UUID) -> ApprovalRequest:
        request = await self._approvals.get_for_user(user_id, request_id)
        if request is None:
            raise ApprovalRequestNotFoundError(str(request_id))
        return await _synchronize_expiration(
            repository=self._approvals,
            request=request,
            now=self._clock.now(),
        )


class ListApprovalRequestsUseCase:
    def __init__(
        self,
        *,
        approvals: ApprovalRequestRepository,
        clock: ClockPort,
    ) -> None:
        self._approvals = approvals
        self._clock = clock

    async def execute(
        self,
        user_id: UUID,
        *,
        status: ApprovalStatus | None = None,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        if not 1 <= limit <= 100:
            raise InvalidApprovalTransitionError("limit must be between 1 and 100.")
        now = self._clock.now()
        items = await self._approvals.list_by_user(user_id, status=None, limit=limit)
        synchronized = [
            await _synchronize_expiration(repository=self._approvals, request=item, now=now)
            for item in items
        ]
        if status is None:
            return tuple(synchronized)
        return tuple(item for item in synchronized if item.effective_status(now) is status)


class ApproveApprovalRequestUseCase:
    def __init__(
        self,
        *,
        approvals: ApprovalRequestRepository,
        clock: ClockPort,
    ) -> None:
        self._approvals = approvals
        self._clock = clock

    async def execute(
        self,
        user_id: UUID,
        request_id: UUID,
        *,
        decision_note: str | None = None,
    ) -> ApprovalRequest:
        request = await self._approvals.get_for_user(user_id, request_id)
        if request is None:
            raise ApprovalRequestNotFoundError(str(request_id))
        now = self._clock.now()
        request = await _synchronize_expiration(
            repository=self._approvals,
            request=request,
            now=now,
        )
        try:
            updated = request.approve(now, decision_note=decision_note)
        except InvalidApprovalRequestError as exc:
            raise InvalidApprovalTransitionError(str(exc.message)) from exc
        await self._approvals.update(updated)
        return updated


class RejectApprovalRequestUseCase:
    def __init__(
        self,
        *,
        approvals: ApprovalRequestRepository,
        clock: ClockPort,
    ) -> None:
        self._approvals = approvals
        self._clock = clock

    async def execute(
        self,
        user_id: UUID,
        request_id: UUID,
        *,
        decision_note: str | None = None,
    ) -> ApprovalRequest:
        request = await self._approvals.get_for_user(user_id, request_id)
        if request is None:
            raise ApprovalRequestNotFoundError(str(request_id))
        now = self._clock.now()
        request = await _synchronize_expiration(
            repository=self._approvals,
            request=request,
            now=now,
        )
        try:
            updated = request.reject(now, decision_note=decision_note)
        except InvalidApprovalRequestError as exc:
            raise InvalidApprovalTransitionError(str(exc.message)) from exc
        await self._approvals.update(updated)
        return updated
