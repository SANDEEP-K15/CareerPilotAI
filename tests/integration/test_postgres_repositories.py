from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.errors import JobAlreadyExistsError
from careerpilot.application.use_cases.get_job import GetJobUseCase
from careerpilot.application.use_cases.get_user import GetUserUseCase
from careerpilot.application.use_cases.persist_job import PersistJobCommand, PersistJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.clock import SystemClock
from careerpilot.infrastructure.ids import Uuid4Generator
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyJobRepository,
    SqlAlchemyUserRepository,
)

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
