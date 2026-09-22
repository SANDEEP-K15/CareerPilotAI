from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.errors import ResumeNotFoundError, UserNotFoundError
from careerpilot.domain.entities.resume import Resume, ResumeContentType
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import ResumeRepository, UserRepository


@dataclass(frozen=True, slots=True)
class AddResumeVersionCommand:
    user_id: UUID
    content: str
    label: str | None = None


class AddResumeVersionUseCase:
    """Append a new immutable version and mark it active. Prior versions stay."""

    def __init__(
        self,
        *,
        users: UserRepository,
        resumes: ResumeRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._users = users
        self._resumes = resumes
        self._clock = clock
        self._ids = ids

    async def execute(self, command: AddResumeVersionCommand) -> Resume:
        if await self._users.get_by_id(command.user_id) is None:
            raise UserNotFoundError(str(command.user_id))
        latest = await self._resumes.latest_version_number(command.user_id)
        version = 1 if latest is None else latest + 1
        resume = Resume.new(
            resume_id=self._ids.new_id(),
            user_id=command.user_id,
            version=version,
            content=command.content,
            created_at=self._clock.now(),
            label=command.label,
            content_type=ResumeContentType.TEXT_PLAIN,
            is_active=False,
        )
        await self._resumes.add(resume)
        await self._resumes.set_active(command.user_id, resume.id)
        activated = await self._resumes.get_by_id(resume.id)
        if activated is None:
            raise ResumeNotFoundError(f"Resume {resume.id} was not found after insert.")
        return activated


class GetActiveResumeUseCase:
    def __init__(self, *, resumes: ResumeRepository) -> None:
        self._resumes = resumes

    async def execute(self, user_id: UUID) -> Resume:
        resume = await self._resumes.get_active_by_user_id(user_id)
        if resume is None:
            raise ResumeNotFoundError(f"No active resume for user {user_id}.")
        return resume


class GetResumeVersionUseCase:
    def __init__(self, *, resumes: ResumeRepository) -> None:
        self._resumes = resumes

    async def execute(self, user_id: UUID, version: int) -> Resume:
        resume = await self._resumes.get_by_user_and_version(user_id, version)
        if resume is None:
            raise ResumeNotFoundError(
                f"Resume version {version} was not found for user {user_id}."
            )
        return resume


class ListResumeVersionsUseCase:
    def __init__(self, *, resumes: ResumeRepository) -> None:
        self._resumes = resumes

    async def execute(self, user_id: UUID) -> tuple[Resume, ...]:
        return await self._resumes.list_by_user_id(user_id)
