from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.errors import JobAlreadyExistsError, JobNotFoundError
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.persistence.postgres.mapping import (
    apply_job_to_model,
    job_from_model,
    job_to_model,
    user_from_model,
    user_to_model,
)
from careerpilot.infrastructure.persistence.postgres.models import JobModel, UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(user_to_model(user))
        await self._session.flush()

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return user_from_model(row) if row is not None else None


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: Job) -> None:
        self._session.add(job_to_model(job))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise JobAlreadyExistsError(job.source.value, job.external_id) from exc

    async def get_by_id(self, job_id: UUID) -> Job | None:
        row = await self._session.get(JobModel, job_id)
        return job_from_model(row) if row is not None else None

    async def get_by_source_identity(self, source: SourceKey, external_id: str) -> Job | None:
        stmt = select(JobModel).where(
            JobModel.source == source.value,
            JobModel.external_id == external_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return job_from_model(row) if row is not None else None

    async def update(self, job: Job) -> None:
        row = await self._session.get(JobModel, job.id)
        if row is None:
            raise JobNotFoundError(str(job.id))
        apply_job_to_model(job, row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise JobAlreadyExistsError(job.source.value, job.external_id) from exc
