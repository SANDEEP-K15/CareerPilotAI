from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.errors import JobAlreadyExistsError
from careerpilot.application.jobs.ingest_types import IngestOutcome
from careerpilot.application.use_cases.get_job import GetJobUseCase
from careerpilot.application.use_cases.get_user import GetUserUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.persist_job import PersistJobCommand, PersistJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.clock import SystemClock
from careerpilot.infrastructure.ids import Uuid4Generator
from careerpilot.infrastructure.persistence.postgres.models import JobModel
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyJobRepository,
    SqlAlchemyUserRepository,
)
from careerpilot.ports.job_source import RawJob
from tests.fakes.clock import FixedIdGenerator, FrozenClock

pytestmark = pytest.mark.integration


async def test_user_roundtrip(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    register = RegisterUserUseCase(users=users, clock=SystemClock(), ids=Uuid4Generator())
    created = await register.execute(RegisterUserCommand(display_name="Ada"))
    await db_session.commit()
    fetched = await GetUserUseCase(users=users).execute(created.id)
    assert fetched.display_name == "Ada"
    assert fetched.created_at.tzinfo is not None


async def test_job_roundtrip_and_duplicate_source_identity(db_session: AsyncSession) -> None:
    jobs = SqlAlchemyJobRepository(db_session)
    persist = PersistJobUseCase(jobs=jobs, clock=SystemClock(), ids=Uuid4Generator())
    created = await persist.execute(
        PersistJobCommand(
            source="example_board",
            external_id="ext-99",
            title="ML Intern",
            company_name="Acme",
            source_url="https://example.com/jobs/99",
            posted_at=datetime(2026, 9, 1, tzinfo=UTC),
            extra={"provider_neutral": True},
        )
    )
    await db_session.commit()
    fetched = await GetJobUseCase(jobs=jobs).execute(created.id)
    assert fetched.external_id == "ext-99"
    assert fetched.extra == {"provider_neutral": True}
    assert fetched.content_hash == created.content_hash

    with pytest.raises(JobAlreadyExistsError):
        await persist.execute(
            PersistJobCommand(
                source="example_board",
                external_id="ext-99",
                title="ML Intern",
                company_name="Acme",
            )
        )


async def test_jobs_unique_source_external_id_at_database(db_session: AsyncSession) -> None:
    jobs = SqlAlchemyJobRepository(db_session)
    now = datetime(2026, 9, 22, tzinfo=UTC)
    first = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("board"),
        external_id="dup",
        title="One",
        company_name="Acme",
        discovered_at=now,
    )
    second = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("board"),
        external_id="dup",
        title="Two",
        company_name="Acme",
        discovered_at=now,
    )
    await jobs.add(first)
    await db_session.commit()
    with pytest.raises(JobAlreadyExistsError) as exc:
        await jobs.add(second)
    assert exc.value.code == "job_already_exists"


async def test_ingest_raw_job_is_idempotent_and_updates_in_place(
    db_session: AsyncSession,
) -> None:
    jobs = SqlAlchemyJobRepository(db_session)
    job_id = uuid4()
    ingest = IngestRawJobUseCase(
        jobs=jobs,
        clock=FrozenClock(datetime(2026, 9, 22, tzinfo=UTC)),
        ids=FixedIdGenerator(job_id),
    )
    raw = RawJob(
        source=SourceKey.parse("example_board"),
        external_id="ingest-1",
        title="ML Intern",
        company_name="Acme",
        source_url="https://example.com/jobs/ingest-1",
        description="v1",
    )
    first = await ingest.execute(raw)
    second = await ingest.execute(raw)
    await db_session.commit()
    assert first.outcome is IngestOutcome.CREATED
    assert second.outcome is IngestOutcome.UNCHANGED
    count = await db_session.scalar(select(func.count()).select_from(JobModel))
    assert count == 1

    changed = RawJob(
        source=SourceKey.parse("example_board"),
        external_id="ingest-1",
        title="Senior ML Intern",
        company_name="Acme",
        source_url="https://example.com/jobs/ingest-1",
        description="v2",
    )
    third = await ingest.execute(changed)
    await db_session.commit()
    assert third.outcome is IngestOutcome.UPDATED
    stored = await jobs.get_by_id(job_id)
    assert stored is not None
    assert stored.title == "Senior ML Intern"
    assert stored.description == "v2"
    count_after = await db_session.scalar(select(func.count()).select_from(JobModel))
    assert count_after == 1
