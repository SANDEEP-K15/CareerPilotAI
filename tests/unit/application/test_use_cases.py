from __future__ import annotations

from uuid import uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.repositories import InMemoryJobRepository, InMemoryUserRepository

from careerpilot.application.errors import (
    JobAlreadyExistsError,
    JobNotFoundError,
    UserNotFoundError,
)
from careerpilot.application.use_cases.get_job import GetJobUseCase
from careerpilot.application.use_cases.get_user import GetUserUseCase
from careerpilot.application.use_cases.persist_job import PersistJobCommand, PersistJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock()


async def test_register_and_get_user(clock: FrozenClock) -> None:
    users = InMemoryUserRepository()
    user_id = uuid4()
    register = RegisterUserUseCase(users=users, clock=clock, ids=FixedIdGenerator(user_id))
    created = await register.execute(RegisterUserCommand(display_name="Ada"))
    fetched = await GetUserUseCase(users=users).execute(user_id)
    assert created.id == user_id
    assert fetched.display_name == "Ada"
    assert fetched.created_at == clock.now()


async def test_get_user_missing() -> None:
    with pytest.raises(UserNotFoundError) as exc:
        await GetUserUseCase(users=InMemoryUserRepository()).execute(uuid4())
    assert exc.value.code == "user_not_found"


async def test_persist_and_get_job(clock: FrozenClock) -> None:
    jobs = InMemoryJobRepository()
    job_id = uuid4()
    persist = PersistJobUseCase(jobs=jobs, clock=clock, ids=FixedIdGenerator(job_id))
    created = await persist.execute(
        PersistJobCommand(
            source="Example Board",
            external_id=" ext-1 ",
            title="ML Intern",
            company_name="Acme",
            source_url="https://example.com/jobs/1",
        )
    )
    fetched = await GetJobUseCase(jobs=jobs).execute(job_id)
    assert created.id == job_id
    assert fetched.source.value == "example_board"
    assert fetched.external_id == "ext-1"
    assert fetched.discovered_at == clock.now()


async def test_persist_job_is_idempotent_on_source_identity(clock: FrozenClock) -> None:
    jobs = InMemoryJobRepository()
    persist = PersistJobUseCase(
        jobs=jobs, clock=clock, ids=FixedIdGenerator(uuid4(), uuid4())
    )
    await persist.execute(
        PersistJobCommand(source="board", external_id="1", title="A", company_name="B")
    )
    with pytest.raises(JobAlreadyExistsError) as exc:
        await persist.execute(
            PersistJobCommand(source="board", external_id="1", title="A", company_name="B")
        )
    assert exc.value.code == "job_already_exists"


async def test_get_job_missing() -> None:
    with pytest.raises(JobNotFoundError):
        await GetJobUseCase(jobs=InMemoryJobRepository()).execute(uuid4())
