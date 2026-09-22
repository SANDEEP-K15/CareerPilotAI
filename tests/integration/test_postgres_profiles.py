from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.errors import CareerProfileAlreadyExistsError
from careerpilot.application.use_cases.career_profile import (
    CreateCareerProfileUseCase,
    GetCareerProfileUseCase,
    SaveCareerProfileCommand,
    SaveCareerProfileUseCase,
)
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.resume import (
    AddResumeVersionCommand,
    AddResumeVersionUseCase,
    GetActiveResumeUseCase,
    GetResumeVersionUseCase,
    ListResumeVersionsUseCase,
)
from careerpilot.infrastructure.persistence.postgres.models import CareerProfileModel, ResumeModel
from careerpilot.infrastructure.persistence.postgres.repositories import (
    SqlAlchemyCareerProfileRepository,
    SqlAlchemyResumeRepository,
    SqlAlchemyUserRepository,
)
from tests.fakes.clock import FixedIdGenerator, FrozenClock

pytestmark = pytest.mark.integration


async def test_profile_and_resume_postgres_constraints(db_session: AsyncSession) -> None:
    users = SqlAlchemyUserRepository(db_session)
    profiles = SqlAlchemyCareerProfileRepository(db_session)
    resumes = SqlAlchemyResumeRepository(db_session)
    clock = FrozenClock()
    user = await RegisterUserUseCase(
        users=users, clock=clock, ids=FixedIdGenerator(uuid4())
    ).execute(RegisterUserCommand(display_name="Ada"))

    save = SaveCareerProfileUseCase(
        users=users, profiles=profiles, clock=clock, ids=FixedIdGenerator(uuid4())
    )
    created = await save.execute(
        SaveCareerProfileCommand(user_id=user.id, skills=("Python",), headline="Intern")
    )
    await db_session.commit()
    fetched = await GetCareerProfileUseCase(profiles=profiles).execute(user.id)
    assert fetched.id == created.id
    updated = await save.execute(
        SaveCareerProfileCommand(user_id=user.id, skills=("Python", "SQL"), headline="Intern")
    )
    await db_session.commit()
    assert updated.id == created.id
    assert updated.skills == ("Python", "SQL")

    create_only = CreateCareerProfileUseCase(
        users=users, profiles=profiles, clock=clock, ids=FixedIdGenerator(uuid4())
    )
    with pytest.raises(CareerProfileAlreadyExistsError):
        await create_only.execute(SaveCareerProfileCommand(user_id=user.id, headline="Nope"))

    add = AddResumeVersionUseCase(
        users=users,
        resumes=resumes,
        clock=clock,
        ids=FixedIdGenerator(uuid4(), uuid4()),
    )
    first = await add.execute(AddResumeVersionCommand(user_id=user.id, content="one"))
    second = await add.execute(AddResumeVersionCommand(user_id=user.id, content="two"))
    await db_session.commit()
    listed = await ListResumeVersionsUseCase(resumes=resumes).execute(user.id)
    assert [item.version for item in listed] == [1, 2]
    assert listed[0].content == "one"
    active = await GetActiveResumeUseCase(resumes=resumes).execute(user.id)
    assert active.id == second.id
    previous = await GetResumeVersionUseCase(resumes=resumes).execute(user.id, 1)
    assert previous.id == first.id
    assert previous.is_active is False

    profile_count = await db_session.scalar(select(func.count()).select_from(CareerProfileModel))
    resume_count = await db_session.scalar(select(func.count()).select_from(ResumeModel))
    assert profile_count == 1
    assert resume_count == 2
