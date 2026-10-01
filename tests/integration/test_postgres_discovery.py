from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.discover_daily_jobs import (
    DiscoverDailyJobsCommand,
    DiscoverDailyJobsUseCase,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.ids import Uuid4Generator
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyCareerProfileRepository,
    SqlAlchemyDailyDiscoveryRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyUserRepository,
)
from careerpilot.ports.job_source import RawJob
from tests.fakes.clock import FrozenClock
from tests.fakes.job_source import InMemoryJobSource

pytestmark = pytest.mark.integration

RUN_ON = date(2026, 10, 1)


async def test_discovery_roundtrip_is_idempotent(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    profiles = SqlAlchemyCareerProfileRepository(db_session)
    jobs = SqlAlchemyJobRepository(db_session)
    discoveries = SqlAlchemyDailyDiscoveryRepository(db_session)
    ids = Uuid4Generator()
    clock = FrozenClock()
    user = await RegisterUserUseCase(users=users, clock=clock, ids=ids).execute(
        RegisterUserCommand(display_name="Ada")
    )
    await profiles.add(
        CareerProfile.new(
            profile_id=uuid4(),
            user_id=user.id,
            now=datetime(2026, 10, 1, tzinfo=UTC),
            skills=("Python",),
            target_titles=("ML Intern",),
            locations=("London",),
        )
    )
    source = InMemoryJobSource(
        "example_board",
        (
            RawJob(
                source=SourceKey.parse("example_board"),
                external_id="ext-1",
                title="ML Intern",
                company_name="Acme",
                location="London",
                description="Python intern role.",
            ),
        ),
    )
    use_case = DiscoverDailyJobsUseCase(
        profiles=profiles,
        jobs=jobs,
        discoveries=discoveries,
        search=SearchAndIngestJobsUseCase(
            search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry((source,))),
            ingest=IngestRawJobUseCase(jobs=jobs, clock=clock, ids=ids),
        ),
        clock=clock,
        ids=ids,
    )
    command = DiscoverDailyJobsCommand(user_id=user.id, run_on=RUN_ON)
    first = await use_case.execute(command)
    second = await use_case.execute(command)
    stored = await discoveries.get_by_user_and_run(user.id, RUN_ON)
    assert stored is not None
    assert first.id == second.id == stored.id
    assert len(stored.selections) == 1
    assert stored.selections[0].score == first.selections[0].score
    assert stored.explanation == first.explanation
    assert len(await jobs.list_active()) == 1
