from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from tests.fakes.repositories import InMemoryCareerProfileRepository, InMemoryJobRepository

from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.application.use_cases.match_jobs import (
    InvalidMatchQueryError,
    MatchJobsCommand,
    MatchJobsUseCase,
)
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


def _profile(user_id: UUID) -> CareerProfile:
    return CareerProfile.new(
        profile_id=uuid4(),
        user_id=user_id,
        now=datetime(2026, 9, 22, tzinfo=UTC),
        headline="ML Intern",
        skills=("Python",),
        target_titles=("ML Intern",),
        locations=("London",),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
    )


def _job(*, external_id: str, **kwargs: object) -> Job:
    payload: dict[str, object] = {
        "job_id": uuid4(),
        "source": SourceKey.parse("example_board"),
        "external_id": external_id,
        "title": "ML Intern",
        "company_name": "Acme",
        "discovered_at": datetime(2026, 9, 22, tzinfo=UTC),
        "description": "Python intern role.",
        "location": "London",
        "remote_policy": RemotePolicy.REMOTE,
        "employment_type": EmploymentType.INTERNSHIP,
    }
    payload.update(kwargs)
    return Job.new(**payload)  # type: ignore[arg-type]


async def test_match_jobs_returns_only_thresholded_active_jobs() -> None:
    user_id = uuid4()
    profiles = InMemoryCareerProfileRepository()
    jobs = InMemoryJobRepository()
    await profiles.add(_profile(user_id))
    good = _job(external_id="good")
    bad_remote = _job(
        external_id="onsite",
        remote_policy=RemotePolicy.ONSITE,
        location="London",
    )
    inactive = _job(external_id="old", status=JobStatus.INACTIVE)
    await jobs.add(good)
    await jobs.add(bad_remote)
    await jobs.add(inactive)
    report = await MatchJobsUseCase(profiles=profiles, jobs=jobs).execute(
        MatchJobsCommand(user_id=user_id, threshold=40, limit=20)
    )
    assert report.considered == 2
    assert report.rejected == 1
    assert [item.job_id for item in report.matches] == [good.id]


async def test_match_jobs_requires_profile() -> None:
    with pytest.raises(CareerProfileNotFoundError):
        await MatchJobsUseCase(
            profiles=InMemoryCareerProfileRepository(),
            jobs=InMemoryJobRepository(),
        ).execute(MatchJobsCommand(user_id=uuid4()))


async def test_match_jobs_validates_query() -> None:
    use_case = MatchJobsUseCase(
        profiles=InMemoryCareerProfileRepository(),
        jobs=InMemoryJobRepository(),
    )
    with pytest.raises(InvalidMatchQueryError):
        await use_case.execute(MatchJobsCommand(user_id=uuid4(), threshold=101))
    with pytest.raises(InvalidMatchQueryError):
        await use_case.execute(MatchJobsCommand(user_id=uuid4(), limit=0))


async def test_empty_catalog_returns_no_matches() -> None:
    user_id = uuid4()
    profiles = InMemoryCareerProfileRepository()
    await profiles.add(_profile(user_id))
    report = await MatchJobsUseCase(
        profiles=profiles, jobs=InMemoryJobRepository()
    ).execute(MatchJobsCommand(user_id=user_id))
    assert report.matches == ()
    assert report.considered == 0
    assert report.rejected == 0
