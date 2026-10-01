from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.use_cases.match_jobs import MatchJobsCommand, MatchJobsUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.ids import Uuid4Generator
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyCareerProfileRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyUserRepository,
)
from tests.fakes.clock import FrozenClock

pytestmark = pytest.mark.integration


async def test_match_against_persisted_jobs(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    profiles = SqlAlchemyCareerProfileRepository(db_session)
    jobs = SqlAlchemyJobRepository(db_session)
    user = await RegisterUserUseCase(
        users=users, clock=FrozenClock(), ids=Uuid4Generator()
    ).execute(RegisterUserCommand(display_name="Ada"))
    await profiles.add(
        CareerProfile.new(
            profile_id=uuid4(),
            user_id=user.id,
            now=datetime(2026, 9, 22, tzinfo=UTC),
            skills=("Python",),
            target_titles=("ML Intern",),
            locations=("London",),
            remote_policy=RemotePolicy.REMOTE,
            employment_type=EmploymentType.INTERNSHIP,
        )
    )
    good = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="match-good",
        title="ML Intern",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Python internship.",
        location="London",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
    )
    blocked = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="match-blocked",
        title="ML Intern",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Python internship.",
        location="London",
        remote_policy=RemotePolicy.ONSITE,
        employment_type=EmploymentType.INTERNSHIP,
    )
    await jobs.add(good)
    await jobs.add(blocked)
    await db_session.commit()
    report = await MatchJobsUseCase(profiles=profiles, jobs=jobs).execute(
        MatchJobsCommand(user_id=user.id)
    )
    assert report.considered == 2
    assert [item.job_id for item in report.matches] == [good.id]
