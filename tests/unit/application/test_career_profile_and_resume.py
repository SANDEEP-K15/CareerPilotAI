from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.repositories import (
    InMemoryCareerProfileRepository,
    InMemoryResumeRepository,
    InMemoryUserRepository,
)

from careerpilot.application.errors import (
    CareerProfileAlreadyExistsError,
    CareerProfileNotFoundError,
    ResumeNotFoundError,
    UserNotFoundError,
)
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
from careerpilot.domain.errors import InvalidProfileError
from careerpilot.domain.value_objects.remote_policy import RemotePolicy


async def _register(
    users: InMemoryUserRepository, user_id: UUID | None = None
) -> UUID:
    uid = user_id or uuid4()
    await RegisterUserUseCase(
        users=users, clock=FrozenClock(), ids=FixedIdGenerator(uid)
    ).execute(RegisterUserCommand(display_name="Ada"))
    return uid


async def test_profile_creation_and_retrieval() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    user_id = await _register(users)
    profile_id = uuid4()
    saved = await SaveCareerProfileUseCase(
        users=users,
        profiles=profiles,
        clock=FrozenClock(),
        ids=FixedIdGenerator(profile_id),
    ).execute(
        SaveCareerProfileCommand(
            user_id=user_id,
            headline="ML intern",
            skills=("Python", "SQL"),
            locations=("Remote",),
            remote_policy=RemotePolicy.REMOTE,
        )
    )
    fetched = await GetCareerProfileUseCase(profiles=profiles).execute(user_id)
    assert saved.id == profile_id == fetched.id
    assert fetched.skills == ("Python", "SQL")
    assert fetched.user_id == user_id


async def test_profile_update_keeps_id_and_created_at() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    user_id = await _register(users)
    save = SaveCareerProfileUseCase(
        users=users,
        profiles=profiles,
        clock=FrozenClock(),
        ids=FixedIdGenerator(uuid4()),
    )
    first = await save.execute(SaveCareerProfileCommand(user_id=user_id, headline="A"))
    second = await save.execute(
        SaveCareerProfileCommand(user_id=user_id, headline="B", skills=("Python",))
    )
    assert first.id == second.id
    assert first.created_at == second.created_at
    assert second.headline == "B"
    assert second.skills == ("Python",)


async def test_profile_validation_rejects_bad_years() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    user_id = await _register(users)
    with pytest.raises(InvalidProfileError):
        await SaveCareerProfileUseCase(
            users=users,
            profiles=profiles,
            clock=FrozenClock(),
            ids=FixedIdGenerator(uuid4()),
        ).execute(SaveCareerProfileCommand(user_id=user_id, years_experience=-1))


async def test_profile_user_isolation() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    a = await _register(users, uuid4())
    b = await _register(users, uuid4())
    await SaveCareerProfileUseCase(
        users=users,
        profiles=profiles,
        clock=FrozenClock(),
        ids=FixedIdGenerator(uuid4()),
    ).execute(SaveCareerProfileCommand(user_id=a, skills=("Python",)))
    with pytest.raises(CareerProfileNotFoundError):
        await GetCareerProfileUseCase(profiles=profiles).execute(b)


async def test_unknown_user_cannot_save_profile() -> None:
    with pytest.raises(UserNotFoundError):
        await SaveCareerProfileUseCase(
            users=InMemoryUserRepository(),
            profiles=InMemoryCareerProfileRepository(),
            clock=FrozenClock(),
            ids=FixedIdGenerator(uuid4()),
        ).execute(SaveCareerProfileCommand(user_id=uuid4()))


async def test_create_profile_rejects_duplicate_user() -> None:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    user_id = await _register(users)
    command = SaveCareerProfileCommand(user_id=user_id, headline="A")
    create = CreateCareerProfileUseCase(
        users=users,
        profiles=profiles,
        clock=FrozenClock(),
        ids=FixedIdGenerator(uuid4(), uuid4()),
    )
    await create.execute(command)
    with pytest.raises(CareerProfileAlreadyExistsError):
        await create.execute(command)


async def test_resume_creation_and_versioning() -> None:
    users = InMemoryUserRepository()
    resumes = InMemoryResumeRepository()
    user_id = await _register(users)
    add = AddResumeVersionUseCase(
        users=users,
        resumes=resumes,
        clock=FrozenClock(),
        ids=FixedIdGenerator(uuid4(), uuid4()),
    )
    first = await add.execute(AddResumeVersionCommand(user_id=user_id, content="v1 body"))
    second = await add.execute(AddResumeVersionCommand(user_id=user_id, content="v2 body"))
    listed = await ListResumeVersionsUseCase(resumes=resumes).execute(user_id)
    assert first.version == 1
    assert second.version == 2
    assert len(listed) == 2
    assert listed[0].content == "v1 body"
    assert listed[1].content == "v2 body"
    active = await GetActiveResumeUseCase(resumes=resumes).execute(user_id)
    assert active.id == second.id
    assert active.is_active is True
    previous = await GetResumeVersionUseCase(resumes=resumes).execute(user_id, 1)
    assert previous.content == "v1 body"
    assert previous.is_active is False


async def test_resume_user_isolation() -> None:
    users = InMemoryUserRepository()
    resumes = InMemoryResumeRepository()
    a = await _register(users, uuid4())
    b = await _register(users, uuid4())
    await AddResumeVersionUseCase(
        users=users,
        resumes=resumes,
        clock=FrozenClock(),
        ids=FixedIdGenerator(uuid4()),
    ).execute(AddResumeVersionCommand(user_id=a, content="secret"))
    with pytest.raises(ResumeNotFoundError):
        await GetActiveResumeUseCase(resumes=resumes).execute(b)
    with pytest.raises(ResumeNotFoundError):
        await GetResumeVersionUseCase(resumes=resumes).execute(b, 1)
    assert await ListResumeVersionsUseCase(resumes=resumes).execute(b) == ()
