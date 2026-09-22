from __future__ import annotations

from uuid import UUID

from careerpilot.application.errors import JobNotFoundError
from careerpilot.domain.entities.job import Job
from careerpilot.ports.repositories import JobRepository


class GetJobUseCase:
    def __init__(self, *, jobs: JobRepository) -> None:
        self._jobs = jobs

    async def execute(self, job_id: UUID) -> Job:
        job = await self._jobs.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(str(job_id))
        return job
