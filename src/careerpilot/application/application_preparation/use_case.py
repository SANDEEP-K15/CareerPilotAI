from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.application_preparation.service import ApplicationPreparationService
from careerpilot.application.errors import (
    CareerProfileNotFoundError,
    JobNotFoundError,
    ResumeNotFoundError,
    UserNotFoundError,
)
from careerpilot.domain.entities.application_prep import ApplicationPrepPackage
from careerpilot.ports.repositories import (
    CareerProfileRepository,
    JobRepository,
    ResumeRepository,
    UserRepository,
)


@dataclass(frozen=True, slots=True)
class PrepareApplicationCommand:
    user_id: UUID
    job_id: UUID
    correlation_id: str | None = None


class PrepareApplicationUseCase:
    """Build an application-prep package without mutating resume or submitting."""

    def __init__(
        self,
        *,
        users: UserRepository,
        profiles: CareerProfileRepository,
        resumes: ResumeRepository,
        jobs: JobRepository,
        preparation: ApplicationPreparationService,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._resumes = resumes
        self._jobs = jobs
        self._preparation = preparation

    async def execute(self, command: PrepareApplicationCommand) -> ApplicationPrepPackage:
        if await self._users.get_by_id(command.user_id) is None:
            raise UserNotFoundError(str(command.user_id))
        profile = await self._profiles.get_by_user_id(command.user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(command.user_id))
        resume = await self._resumes.get_active_by_user_id(command.user_id)
        if resume is None:
            raise ResumeNotFoundError(f"No active resume for user {command.user_id}.")
        job = await self._jobs.get_by_id(command.job_id)
        if job is None:
            raise JobNotFoundError(str(command.job_id))
        return await self._preparation.prepare(
            profile=profile,
            job=job,
            resume=resume,
            correlation_id=command.correlation_id,
        )
