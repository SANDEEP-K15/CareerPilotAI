from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from tests.fakes.llm import CodedLlmFailureProvider, FakeLlmProvider
from tests.fakes.repositories import InMemoryCareerProfileRepository, InMemoryJobRepository

from careerpilot.application.llm import (
    InvokeLlmUseCase,
    LlmProviderRegistry,
    LlmRuntimeConfiguration,
)
from careerpilot.application.matching.semantic import (
    SemanticMatchingService,
    SemanticMatchJobsCommand,
    SemanticMatchJobsUseCase,
)
from careerpilot.application.use_cases.match_jobs import MatchJobsCommand, MatchJobsUseCase
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.hybrid_matching import combine_match_scores
from careerpilot.domain.matching import match_job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.llm import LlmRequest, LlmResponse


def _profile(user_id: UUID) -> CareerProfile:
    return CareerProfile.new(
        profile_id=uuid4(),
        user_id=user_id,
        now=datetime(2026, 9, 22, tzinfo=UTC),
        headline="Backend Engineer",
        skills=("Python", "PostgreSQL"),
        target_titles=("Backend Engineer",),
        locations=("Remote",),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )


def _job(*, external_id: str, title: str, description: str) -> Job:
    return Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id=external_id,
        title=title,
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description=description,
        location="Remote",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
    )


def _semantic_llm(*, alignment_score: int) -> FakeLlmProvider:
    payload = json.dumps(
        {
            "alignment_score": alignment_score,
            "summary": "Semantic assessment",
            "concerns": ["verify domain depth"],
        }
    )
    return FakeLlmProvider("lab", response_text=payload)


def _use_case(
    *,
    profiles: InMemoryCareerProfileRepository,
    jobs: InMemoryJobRepository,
    provider: FakeLlmProvider | CodedLlmFailureProvider,
) -> SemanticMatchJobsUseCase:
    registry = LlmProviderRegistry((provider,))
    configuration = LlmRuntimeConfiguration(
        default_provider=provider.provider_key,
        default_model=LlmModelId.parse("demo-model"),
    )
    llm = InvokeLlmUseCase(registry=registry, configuration=configuration)
    return SemanticMatchJobsUseCase(
        profiles=profiles,
        jobs=jobs,
        semantic=SemanticMatchingService(llm=llm),
    )


async def test_semantic_match_applies_llm_and_combines_scores() -> None:
    user_id = uuid4()
    profiles = InMemoryCareerProfileRepository()
    jobs = InMemoryJobRepository()
    await profiles.add(_profile(user_id))
    job = _job(
        external_id="one",
        title="Backend Engineer",
        description="Python and PostgreSQL services.",
    )
    await jobs.add(job)
    profile = await profiles.get_by_user_id(user_id)
    assert profile is not None
    deterministic = match_job(profile, job)
    expected = combine_match_scores(
        deterministic=deterministic.score,
        semantic_alignment=88,
    )
    report = await _use_case(
        profiles=profiles,
        jobs=jobs,
        provider=_semantic_llm(alignment_score=88),
    ).execute(SemanticMatchJobsCommand(user_id=user_id, threshold=0, limit=10))
    assert report.semantic_applied_count == 1
    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.semantic_applied is True
    assert match.semantic is not None
    assert match.semantic.alignment_score == 88
    assert match.combined_score == expected


async def test_semantic_match_falls_back_when_llm_fails() -> None:
    user_id = uuid4()
    profiles = InMemoryCareerProfileRepository()
    jobs = InMemoryJobRepository()
    await profiles.add(_profile(user_id))
    job = _job(
        external_id="one",
        title="Backend Engineer",
        description="Python and PostgreSQL services.",
    )
    await jobs.add(job)
    baseline = await MatchJobsUseCase(profiles=profiles, jobs=jobs).execute(
        MatchJobsCommand(user_id=user_id, threshold=0, limit=10)
    )
    report = await _use_case(
        profiles=profiles,
        jobs=jobs,
        provider=CodedLlmFailureProvider("lab"),
    ).execute(SemanticMatchJobsCommand(user_id=user_id, threshold=0, limit=10))
    assert report.semantic_applied_count == 0
    assert report.semantic_fallback_count == 1
    assert len(report.matches) == len(baseline.matches)
    assert report.matches[0].combined_score == baseline.matches[0].score
    assert report.matches[0].semantic is None


async def test_semantic_match_can_reorder_by_combined_score() -> None:
    user_id = uuid4()
    profiles = InMemoryCareerProfileRepository()
    jobs = InMemoryJobRepository()
    await profiles.add(_profile(user_id))
    profile = await profiles.get_by_user_id(user_id)
    assert profile is not None
    stronger_det = _job(
        external_id="strong-det",
        title="Backend Engineer",
        description="Python PostgreSQL platform.",
    )
    weaker_det = _job(
        external_id="weak-det",
        title="Backend Engineer",
        description="PostgreSQL and general development role.",
    )
    await jobs.add(stronger_det)
    await jobs.add(weaker_det)
    strong_score = match_job(profile, stronger_det).score
    weak_score = match_job(profile, weaker_det).score
    weak_combined = combine_match_scores(deterministic=weak_score, semantic_alignment=95)
    strong_combined = combine_match_scores(
        deterministic=strong_score,
        semantic_alignment=5,
    )
    assert weak_combined > strong_combined
    boost_id = str(weaker_det.id)

    class JobSpecificSemanticLlm(FakeLlmProvider):
        async def complete(self, request: LlmRequest) -> LlmResponse:
            alignment = 95 if request.metadata.get("job_id") == boost_id else 5
            self._response_text = json.dumps(
                {
                    "alignment_score": alignment,
                    "summary": "fit",
                    "concerns": [],
                }
            )
            return await super().complete(request)

    report = await _use_case(
        profiles=profiles,
        jobs=jobs,
        provider=JobSpecificSemanticLlm("lab"),
    ).execute(SemanticMatchJobsCommand(user_id=user_id, threshold=0, limit=10))
    assert report.matches[0].deterministic.job_id == weaker_det.id
