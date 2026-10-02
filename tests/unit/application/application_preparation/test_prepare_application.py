from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.llm import CodedLlmFailureProvider, FakeLlmProvider
from tests.fakes.repositories import (
    InMemoryCareerProfileRepository,
    InMemoryJobRepository,
    InMemoryResumeRepository,
    InMemoryUserRepository,
)

from careerpilot.application.application_preparation import (
    ApplicationPreparationFailedError,
    ApplicationPreparationService,
    PrepareApplicationCommand,
    PrepareApplicationUseCase,
)
from careerpilot.application.llm import (
    InvokeLlmUseCase,
    LlmProviderRegistry,
    LlmRuntimeConfiguration,
)
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.resume import (
    AddResumeVersionCommand,
    AddResumeVersionUseCase,
)
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.cost import CostManagerPort, LlmUsageEvent


def _prep_payload() -> str:
    return json.dumps(
        {
            "guidance": "Focus on backend impact and metrics.",
            "talking_points": [
                {"section": "experience", "point": "Connect Python work to job stack."}
            ],
            "interview_questions": [
                {
                    "question": "Tell me about a scalable service you built.",
                    "focus": "Prepare a STAR story from resume.",
                }
            ],
        }
    )


def _profile(user_id: UUID) -> CareerProfile:
    return CareerProfile.new(
        profile_id=uuid4(),
        user_id=user_id,
        now=datetime(2026, 9, 22, tzinfo=UTC),
        headline="Backend Engineer",
        skills=("Python", "PostgreSQL"),
        target_titles=("Backend Engineer",),
    )


def _job() -> Job:
    return Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="ext-prep",
        title="Backend Engineer",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Python services.",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )


class RecordingCostManager(CostManagerPort):
    def __init__(self) -> None:
        self.events: list[LlmUsageEvent] = []

    async def record_llm_usage(self, event: LlmUsageEvent) -> None:
        self.events.append(event)


async def _seed_user_with_resume(
    *,
    users: InMemoryUserRepository,
    profiles: InMemoryCareerProfileRepository,
    resumes: InMemoryResumeRepository,
) -> tuple[UUID, str]:
    user_id = uuid4()
    clock = FrozenClock()
    ids = FixedIdGenerator(*[uuid4() for _ in range(8)])
    await RegisterUserUseCase(users=users, clock=clock, ids=FixedIdGenerator(user_id)).execute(
        RegisterUserCommand(display_name="Ada")
    )
    await profiles.add(_profile(user_id))
    original = "Original resume for prep"
    resume = await AddResumeVersionUseCase(
        users=users, resumes=resumes, clock=clock, ids=ids
    ).execute(AddResumeVersionCommand(user_id=user_id, content=original))
    return user_id, resume.content


def _use_case(
    *,
    users: InMemoryUserRepository,
    profiles: InMemoryCareerProfileRepository,
    resumes: InMemoryResumeRepository,
    jobs: InMemoryJobRepository,
    provider: FakeLlmProvider | CodedLlmFailureProvider,
    cost_manager: CostManagerPort | None = None,
) -> PrepareApplicationUseCase:
    registry = LlmProviderRegistry((provider,))
    configuration = LlmRuntimeConfiguration(
        default_provider=provider.provider_key,
        default_model=LlmModelId.parse("demo-model"),
    )
    llm = InvokeLlmUseCase(
        registry=registry,
        configuration=configuration,
        cost_manager=cost_manager,
    )
    return PrepareApplicationUseCase(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        preparation=ApplicationPreparationService(llm=llm),
    )


async def test_prepare_application_returns_package() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, original = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    package = await _use_case(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        provider=FakeLlmProvider("lab", response_text=_prep_payload()),
    ).execute(PrepareApplicationCommand(user_id=user_id, job_id=job.id))
    assert "backend impact" in package.guidance.lower()
    assert len(package.talking_points) == 1
    assert len(package.interview_questions) == 1
    active = await resumes.get_active_by_user_id(user_id)
    assert active is not None
    assert active.content == original


async def test_prepare_application_fails_when_llm_fails() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, _ = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    with pytest.raises(ApplicationPreparationFailedError):
        await _use_case(
            users=users,
            profiles=profiles,
            resumes=resumes,
            jobs=jobs,
            provider=CodedLlmFailureProvider("lab"),
        ).execute(PrepareApplicationCommand(user_id=user_id, job_id=job.id))


async def test_prepare_application_fails_on_invalid_json() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, _ = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    with pytest.raises(ApplicationPreparationFailedError):
        await _use_case(
            users=users,
            profiles=profiles,
            resumes=resumes,
            jobs=jobs,
            provider=FakeLlmProvider("lab", response_text="broken"),
        ).execute(PrepareApplicationCommand(user_id=user_id, job_id=job.id))


async def test_prepare_application_records_llm_usage() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, _ = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    cost_manager = RecordingCostManager()
    await _use_case(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        provider=FakeLlmProvider("lab", response_text=_prep_payload(), include_reported_cost=True),
        cost_manager=cost_manager,
    ).execute(
        PrepareApplicationCommand(user_id=user_id, job_id=job.id, correlation_id="corr-prep")
    )
    assert len(cost_manager.events) == 1
    assert cost_manager.events[0].task == "application_preparation"
    assert cost_manager.events[0].correlation_id == "corr-prep"
    assert cost_manager.events[0].usage.reported_cost is not None
    assert cost_manager.events[0].usage.reported_cost.amount == Decimal("0.001")
