from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from careerpilot.domain.entities.approval_request import ApprovalRequest
from careerpilot.domain.errors import InvalidApprovalRequestError
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus


def _pending(*, expires_in: timedelta = timedelta(hours=1)) -> ApprovalRequest:
    now = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
    return ApprovalRequest.new(
        request_id=uuid4(),
        user_id=uuid4(),
        job_id=uuid4(),
        action=ApprovalAction.SUBMIT_APPLICATION,
        created_at=now,
        expires_at=now + expires_in,
        reason="Apply when ready",
    )


def test_effective_status_becomes_expired_after_deadline() -> None:
    request = _pending(expires_in=timedelta(minutes=30))
    now = datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
    assert request.effective_status(now) is ApprovalStatus.EXPIRED


def test_approve_only_from_pending() -> None:
    request = _pending()
    now = datetime(2026, 9, 22, 8, 30, tzinfo=UTC)
    approved = request.approve(now, decision_note="Looks good")
    assert approved.status is ApprovalStatus.APPROVED
    assert approved.decided_at == now
    with pytest.raises(InvalidApprovalRequestError):
        approved.approve(now)


def test_reject_expired_pending_fails() -> None:
    request = _pending(expires_in=timedelta(minutes=5))
    now = datetime(2026, 9, 22, 10, 0, tzinfo=UTC)
    with pytest.raises(InvalidApprovalRequestError):
        request.reject(now)
