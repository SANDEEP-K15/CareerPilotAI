from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.errors import (
    CareerProfileNotFoundError,
    JobNotFoundError,
    ResumeNotFoundError,
    UserNotFoundError,
)
from careerpilot.application.resume_tailoring.service import ResumeTailoringService
from careerpilot.domain.entities.resume_tailoring import ResumeTailoringResult
from careerpilot.ports.repositories import (
    CareerProfileRepository,
    JobRepository,
    ResumeRepository,
    UserRepository,
)


@dataclass(frozen=True, slots=True)
class TailorResumeCommand:
    user_id: UUID
    job_id: UUID
    correlation_id: str | None = None


class TailorResumeUseCase:
    """Tailor the user's active resume for a job without mutating stored versions."""

    def __init__(
        self,
        *,
        users: UserRepository,
        profiles: CareerProfileRepository,
        resumes: ResumeRepository,
        jobs: JobRepository,
        tailoring: ResumeTailoringService,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._resumes = resumes
        self._jobs = jobs
        self._tailoring = tailoring

    async def execute(self, command: TailorResumeCommand) -> ResumeTailoringResult:
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
        return await self._tailoring.tailor(
            profile=profile,
            job=job,
            resume=resume,
            correlation_id=command.correlation_id,
        )
