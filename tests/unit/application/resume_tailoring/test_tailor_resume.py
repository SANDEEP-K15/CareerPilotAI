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

from careerpilot.application.llm import (
    InvokeLlmUseCase,
    LlmProviderRegistry,
    LlmRuntimeConfiguration,
)
from careerpilot.application.resume_tailoring import (
    ResumeTailoringFailedError,
    ResumeTailoringService,
    TailorResumeCommand,
    TailorResumeUseCase,
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


def _tailor_payload(*, content: str = "Tailored resume text") -> str:
    return json.dumps(
        {
            "tailored_content": content,
            "changes": [
                {"section": "summary", "description": "Aligned summary with job keywords."}
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
        external_id="ext-tailor",
        title="Backend Engineer",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Python services and PostgreSQL.",
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
    original = "Original resume content v1"
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
) -> TailorResumeUseCase:
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
    return TailorResumeUseCase(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        tailoring=ResumeTailoringService(llm=llm),
    )


async def test_tailor_resume_returns_structured_output() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, original_content = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    provider = FakeLlmProvider("lab", response_text=_tailor_payload())
    result = await _use_case(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        provider=provider,
    ).execute(TailorResumeCommand(user_id=user_id, job_id=job.id))
    assert result.tailored_content == "Tailored resume text"
    assert result.source_resume_version == 1
    assert len(result.changes) == 1
    active = await resumes.get_active_by_user_id(user_id)
    assert active is not None
    assert active.content == original_content
    assert len(await resumes.list_by_user_id(user_id)) == 1


async def test_tailor_resume_fails_when_llm_fails() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, _ = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    with pytest.raises(ResumeTailoringFailedError):
        await _use_case(
            users=users,
            profiles=profiles,
            resumes=resumes,
            jobs=jobs,
            provider=CodedLlmFailureProvider("lab"),
        ).execute(TailorResumeCommand(user_id=user_id, job_id=job.id))


async def test_tailor_resume_fails_on_invalid_llm_json() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    jobs = InMemoryJobRepository()
    user_id, _ = await _seed_user_with_resume(
        users=users, profiles=profiles, resumes=resumes
    )
    job = _job()
    await jobs.add(job)
    with pytest.raises(ResumeTailoringFailedError):
        await _use_case(
            users=users,
            profiles=profiles,
            resumes=resumes,
            jobs=jobs,
            provider=FakeLlmProvider("lab", response_text="not json"),
        ).execute(TailorResumeCommand(user_id=user_id, job_id=job.id))


async def test_tailor_resume_records_llm_usage() -> None:
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
    provider = FakeLlmProvider("lab", response_text=_tailor_payload(), include_reported_cost=True)
    await _use_case(
        users=users,
        profiles=profiles,
        resumes=resumes,
        jobs=jobs,
        provider=provider,
        cost_manager=cost_manager,
    ).execute(TailorResumeCommand(user_id=user_id, job_id=job.id, correlation_id="corr-1"))
    assert len(cost_manager.events) == 1
    event = cost_manager.events[0]
    assert event.task == "resume_tailoring"
    assert event.correlation_id == "corr-1"
    assert event.usage.reported_cost is not None
    assert event.usage.reported_cost.amount == Decimal("0.001")
