from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.llm import FakeLlmProvider
from tests.fakes.repositories import (
    InMemoryCareerProfileRepository,
    InMemoryJobRepository,
    InMemoryResumeRepository,
    InMemoryUserRepository,
)

from careerpilot.api.app import create_app
from careerpilot.api.deps import ProfileApi
from careerpilot.application.application_preparation import (
    ApplicationPreparationService,
    PrepareApplicationUseCase,
)
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.llm import (
    InvokeLlmUseCase,
    LlmProviderRegistry,
    LlmRuntimeConfiguration,
)
from careerpilot.application.use_cases.career_profile import (
    GetCareerProfileUseCase,
    SaveCareerProfileUseCase,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.resume import (
    AddResumeVersionUseCase,
    GetActiveResumeUseCase,
    GetResumeVersionUseCase,
    ListResumeVersionsUseCase,
)
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


def _prep_client() -> tuple[TestClient, InMemoryUserRepository, InMemoryJobRepository]:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    clock = FrozenClock()
    ids = FixedIdGenerator(*[uuid4() for _ in range(16)])
    search = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(())),
        ingest=IngestRawJobUseCase(jobs=jobs, clock=clock, ids=FixedIdGenerator(uuid4())),
    )
    provider = FakeLlmProvider(
        "lab",
        response_text=json.dumps(
            {
                "guidance": "API prep guidance",
                "talking_points": [{"section": "skills", "point": "Python depth"}],
                "interview_questions": [
                    {"question": "Why this role?", "focus": "Motivation and fit"}
                ],
            }
        ),
    )
    llm = InvokeLlmUseCase(
        registry=LlmProviderRegistry((provider,)),
        configuration=LlmRuntimeConfiguration(
            default_provider=provider.provider_key,
            default_model=LlmModelId.parse("demo-model"),
        ),
    )
    prepare = PrepareApplicationUseCase(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        preparation=ApplicationPreparationService(llm=llm),
    )
    profile_api = ProfileApi(
        save_profile=SaveCareerProfileUseCase(
            users=users, profiles=profiles, clock=clock, ids=ids
        ),
        get_profile=GetCareerProfileUseCase(profiles=profiles),
        add_resume=AddResumeVersionUseCase(users=users, resumes=resumes, clock=clock, ids=ids),
        get_active_resume=GetActiveResumeUseCase(resumes=resumes),
        get_resume_version=GetResumeVersionUseCase(resumes=resumes),
        list_resumes=ListResumeVersionsUseCase(resumes=resumes),
    )
    app = create_app(
        search_jobs=search,
        profile_api=profile_api,
        prepare_application=prepare,
    )
    return TestClient(app), users, jobs


async def _seed(
    users: InMemoryUserRepository,
    jobs: InMemoryJobRepository,
    client: TestClient,
) -> tuple[UUID, UUID]:
    user_id = uuid4()
    await RegisterUserUseCase(
        users=users, clock=FrozenClock(), ids=FixedIdGenerator(user_id)
    ).execute(RegisterUserCommand(display_name="Ada"))
    client.put(
        f"/api/v1/users/{user_id}/profile",
        json={"headline": "Engineer", "skills": ["Python"]},
    )
    client.post(
        f"/api/v1/users/{user_id}/resumes",
        json={"content": "Resume for prep", "label": "base"},
    )
    job = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="prep-job",
        title="Engineer",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Role details",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )
    await jobs.add(job)
    return user_id, job.id


def test_prepare_application_api_returns_package() -> None:
    client, users, jobs = _prep_client()
    user_id, job_id = asyncio.run(_seed(users, jobs, client))
    response = client.post(
        f"/api/v1/users/{user_id}/applications/prepare",
        json={"job_id": str(job_id)},
        headers={"X-Request-ID": "req-prep-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guidance"] == "API prep guidance"
    assert body["request_id"] == "req-prep-1"
    assert body["interview_questions"][0]["question"] == "Why this role?"
    active = client.get(f"/api/v1/users/{user_id}/resumes/active")
    assert active.json()["content"] == "Resume for prep"


def test_prepare_application_api_not_configured() -> None:
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
        f"/api/v1/users/{uuid4()}/applications/prepare",
        json={"job_id": str(uuid4())},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "not_configured"
