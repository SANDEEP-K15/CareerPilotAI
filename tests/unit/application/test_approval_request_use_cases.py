from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.repositories import (
    InMemoryApprovalRequestRepository,
    InMemoryJobRepository,
    InMemoryUserRepository,
)

from careerpilot.application.errors import (
    ApprovalRequestNotFoundError,
    DuplicatePendingApprovalError,
    InvalidApprovalTransitionError,
)
from careerpilot.application.use_cases.approval_requests import (
    ApproveApprovalRequestUseCase,
    CreateApprovalRequestUseCase,
    GetApprovalRequestUseCase,
    ListApprovalRequestsUseCase,
    RejectApprovalRequestUseCase,
)
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


async def _user_and_job() -> tuple[InMemoryUserRepository, InMemoryJobRepository, UUID, UUID]:
    users = InMemoryUserRepository()
    jobs = InMemoryJobRepository()
    user_id = uuid4()
    await RegisterUserUseCase(
        users=users, clock=FrozenClock(), ids=FixedIdGenerator(user_id)
    ).execute(RegisterUserCommand(display_name="Ada"))
    job = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="approval-job",
        title="Engineer",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )
    await jobs.add(job)
    return users, jobs, user_id, job.id


def _create(
    users: InMemoryUserRepository,
    jobs: InMemoryJobRepository,
    approvals: InMemoryApprovalRequestRepository,
    clock: FrozenClock,
) -> CreateApprovalRequestUseCase:
    class _Ids:
        def new_id(self) -> UUID:
            return uuid4()

    return CreateApprovalRequestUseCase(
        users=users,
        jobs=jobs,
        approvals=approvals,
        clock=clock,
        ids=_Ids(),
    )


async def test_create_and_approve_request() -> None:
    users, jobs, user_id, job_id = await _user_and_job()
    approvals = InMemoryApprovalRequestRepository()
    clock = FrozenClock()
    created = await _create(users, jobs, approvals, clock).execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
        reason="Ready to apply",
    )
    assert created.status is ApprovalStatus.PENDING
    approved = await ApproveApprovalRequestUseCase(
        approvals=approvals, clock=clock
    ).execute(user_id, created.id, decision_note="Approved for submission later")
    assert approved.status is ApprovalStatus.APPROVED


async def test_duplicate_pending_is_rejected() -> None:
    users, jobs, user_id, job_id = await _user_and_job()
    approvals = InMemoryApprovalRequestRepository()
    clock = FrozenClock()
    create = _create(users, jobs, approvals, clock)
    await create.execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
    )
    with pytest.raises(DuplicatePendingApprovalError):
        await create.execute(
            user_id=user_id,
            job_id=job_id,
            action=ApprovalAction.SUBMIT_APPLICATION,
        )


async def test_expired_request_cannot_be_approved() -> None:
    users, jobs, user_id, job_id = await _user_and_job()
    approvals = InMemoryApprovalRequestRepository()
    start = datetime(2026, 9, 22, 8, 0, tzinfo=UTC)
    clock = FrozenClock(start)
    create = _create(users, jobs, approvals, clock)
    created = await create.execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
        expires_at=start + timedelta(minutes=30),
    )
    clock = FrozenClock(start + timedelta(hours=1))
    with pytest.raises(InvalidApprovalTransitionError):
        await ApproveApprovalRequestUseCase(approvals=approvals, clock=clock).execute(
            user_id, created.id
        )
    fetched = await GetApprovalRequestUseCase(approvals=approvals, clock=clock).execute(
        user_id, created.id
    )
    assert fetched.status is ApprovalStatus.EXPIRED


async def test_reject_request() -> None:
    users, jobs, user_id, job_id = await _user_and_job()
    approvals = InMemoryApprovalRequestRepository()
    clock = FrozenClock()
    created = await _create(users, jobs, approvals, clock).execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
    )
    rejected = await RejectApprovalRequestUseCase(
        approvals=approvals, clock=clock
    ).execute(user_id, created.id, decision_note="Not now")
    assert rejected.status is ApprovalStatus.REJECTED


async def test_list_filters_by_status() -> None:
    users, jobs, user_id, job_id = await _user_and_job()
    approvals = InMemoryApprovalRequestRepository()
    clock = FrozenClock()
    create = _create(users, jobs, approvals, clock)
    first = await create.execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
    )
    await ApproveApprovalRequestUseCase(approvals=approvals, clock=clock).execute(
        user_id, first.id
    )
    clock = FrozenClock(datetime(2026, 9, 23, tzinfo=UTC))
    create = _create(users, jobs, approvals, clock)
    await create.execute(
        user_id=user_id,
        job_id=job_id,
        action=ApprovalAction.SUBMIT_APPLICATION,
    )
    pending = await ListApprovalRequestsUseCase(approvals=approvals, clock=clock).execute(
        user_id, status=ApprovalStatus.PENDING
    )
    assert len(pending) == 1


async def test_get_missing_returns_not_found() -> None:
    approvals = InMemoryApprovalRequestRepository()
    with pytest.raises(ApprovalRequestNotFoundError):
        await GetApprovalRequestUseCase(
            approvals=approvals, clock=FrozenClock()
        ).execute(uuid4(), uuid4())
