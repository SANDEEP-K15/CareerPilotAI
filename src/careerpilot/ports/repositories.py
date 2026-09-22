from __future__ import annotations

from typing import Protocol
from uuid import UUID

from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.source_key import SourceKey


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...


class JobRepository(Protocol):
    async def add(self, job: Job) -> None: ...

    async def get_by_id(self, job_id: UUID) -> Job | None: ...

    async def get_by_source_identity(self, source: SourceKey, external_id: str) -> Job | None: ...
