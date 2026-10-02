from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.repositories import (
    InMemoryApprovalRequestRepository,
    InMemoryJobRepository,
    InMemoryUserRepository,
)

from careerpilot.api.app import create_app
from careerpilot.api.deps_approvals import ApprovalApi
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.approval_requests import (
    ApproveApprovalRequestUseCase,
    CreateApprovalRequestUseCase,
    GetApprovalRequestUseCase,
    ListApprovalRequestsUseCase,
    RejectApprovalRequestUseCase,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


def _client() -> tuple[TestClient, InMemoryUserRepository, InMemoryJobRepository]:
    users = InMemoryUserRepository()
    jobs = InMemoryJobRepository()
    approvals = InMemoryApprovalRequestRepository()
    clock = FrozenClock()
    ids = FixedIdGenerator(*[uuid4() for _ in range(8)])
    search = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(())),
        ingest=IngestRawJobUseCase(jobs=jobs, clock=clock, ids=FixedIdGenerator(uuid4())),
    )
    approval_api = ApprovalApi(
        create_request=CreateApprovalRequestUseCase(
            users=users, jobs=jobs, approvals=approvals, clock=clock, ids=ids
        ),
        get_request=GetApprovalRequestUseCase(approvals=approvals, clock=clock),
        list_requests=ListApprovalRequestsUseCase(approvals=approvals, clock=clock),
        approve_request=ApproveApprovalRequestUseCase(approvals=approvals, clock=clock),
        reject_request=RejectApprovalRequestUseCase(approvals=approvals, clock=clock),
    )
    app = create_app(search_jobs=search, approval_api=approval_api)
    return TestClient(app), users, jobs


async def _seed(users: InMemoryUserRepository, jobs: InMemoryJobRepository) -> tuple[UUID, UUID]:
    user_id = uuid4()
    await RegisterUserUseCase(
        users=users, clock=FrozenClock(), ids=FixedIdGenerator(user_id)
    ).execute(RegisterUserCommand(display_name="Ada"))
    job = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="api-approval",
        title="Engineer",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )
    await jobs.add(job)
    return user_id, job.id


def test_approval_request_api_lifecycle() -> None:
    client, users, jobs = _client()
    user_id, job_id = asyncio.run(_seed(users, jobs))
    created = client.post(
        f"/api/v1/users/{user_id}/approval-requests",
        json={
            "job_id": str(job_id),
            "action": "submit_application",
            "reason": "Please review",
        },
        headers={"X-Request-ID": "req-approval-1"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "pending"
    request_id = body["id"]
    approved = client.post(
        f"/api/v1/users/{user_id}/approval-requests/{request_id}/approve",
        json={"decision_note": "OK for future submit"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    listed = client.get(f"/api/v1/users/{user_id}/approval-requests")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


def test_approval_api_not_configured() -> None:
    search = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(())),
        ingest=IngestRawJobUseCase(
            jobs=InMemoryJobRepository(),
            clock=FrozenClock(),
            ids=FixedIdGenerator(uuid4()),
        ),
    )
    client = TestClient(create_app(search_jobs=search))
    response = client.post(
        f"/api/v1/users/{uuid4()}/approval-requests",
        json={"job_id": str(uuid4()), "action": "submit_application"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "not_configured"
