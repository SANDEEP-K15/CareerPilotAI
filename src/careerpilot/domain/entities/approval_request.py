from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID

from careerpilot.domain.errors import InvalidApprovalRequestError
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus

DEFAULT_APPROVAL_TTL = timedelta(days=7)
_MAX_NOTE = 500


@dataclass(slots=True)
class ApprovalRequest:
    """Human approval record. Granting approval does not execute the action (M20+)."""

    id: UUID
    user_id: UUID
    job_id: UUID
    action: ApprovalAction
    status: ApprovalStatus
    reason: str | None
    decision_note: str | None
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None

    @classmethod
    def new(
        cls,
        *,
        request_id: UUID,
        user_id: UUID,
        job_id: UUID,
        action: ApprovalAction,
        created_at: datetime,
        expires_at: datetime,
        reason: str | None = None,
    ) -> ApprovalRequest:
        _require_aware(created_at, field="created_at")
        _require_aware(expires_at, field="expires_at")
        if expires_at <= created_at:
            raise InvalidApprovalRequestError("expires_at must be after created_at.")
        return cls(
            id=request_id,
            user_id=user_id,
            job_id=job_id,
            action=action,
            status=ApprovalStatus.PENDING,
            reason=_optional_note(reason, field="reason"),
            decision_note=None,
            created_at=created_at,
            updated_at=created_at,
            expires_at=expires_at,
            decided_at=None,
        )

    def effective_status(self, now: datetime) -> ApprovalStatus:
        _require_aware(now, field="now")
        if self.status is ApprovalStatus.PENDING and now >= self.expires_at:
            return ApprovalStatus.EXPIRED
        return self.status

    def mark_expired(self, now: datetime) -> ApprovalRequest:
        if self.status is not ApprovalStatus.PENDING:
            return self
        if now < self.expires_at:
            raise InvalidApprovalRequestError("approval request is not yet expired.")
        return replace(
            self,
            status=ApprovalStatus.EXPIRED,
            updated_at=now,
        )

    def approve(self, now: datetime, *, decision_note: str | None = None) -> ApprovalRequest:
        status = self.effective_status(now)
        if status is not ApprovalStatus.PENDING:
            raise InvalidApprovalRequestError(
                f"Cannot approve request in status {status.value}."
            )
        return replace(
            self,
            status=ApprovalStatus.APPROVED,
            decision_note=_optional_note(decision_note, field="decision_note"),
            updated_at=now,
            decided_at=now,
        )

    def reject(self, now: datetime, *, decision_note: str | None = None) -> ApprovalRequest:
        status = self.effective_status(now)
        if status is not ApprovalStatus.PENDING:
            raise InvalidApprovalRequestError(
                f"Cannot reject request in status {status.value}."
            )
        return replace(
            self,
            status=ApprovalStatus.REJECTED,
            decision_note=_optional_note(decision_note, field="decision_note"),
            updated_at=now,
            decided_at=now,
        )


def _optional_note(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    trimmed = " ".join(value.split())
    if not trimmed:
        return None
    if len(trimmed) > _MAX_NOTE:
        raise InvalidApprovalRequestError(f"{field} must be at most {_MAX_NOTE} characters.")
    return trimmed


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidApprovalRequestError(f"{field} must be timezone-aware UTC datetime.")
