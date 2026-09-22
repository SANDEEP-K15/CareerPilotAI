from __future__ import annotations

from uuid import UUID

from careerpilot.application.errors import JobAlreadyExistsError
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.source_key import SourceKey


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self._users[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)


class InMemoryJobRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Job] = {}
        self._by_source: dict[tuple[str, str], UUID] = {}

    async def add(self, job: Job) -> None:
        key = (job.source.value, job.external_id)
        if key in self._by_source:
            raise JobAlreadyExistsError(job.source.value, job.external_id)
        self._by_id[job.id] = job
        self._by_source[key] = job.id

    async def get_by_id(self, job_id: UUID) -> Job | None:
        return self._by_id.get(job_id)

    async def get_by_source_identity(self, source: SourceKey, external_id: str) -> Job | None:
        job_id = self._by_source.get((source.value, external_id))
        if job_id is None:
            return None
        return self._by_id.get(job_id)
