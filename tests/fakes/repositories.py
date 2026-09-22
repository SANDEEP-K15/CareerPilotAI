from __future__ import annotations

from uuid import UUID

from careerpilot.application.errors import (
    CareerProfileAlreadyExistsError,
    CareerProfileNotFoundError,
    JobAlreadyExistsError,
    JobNotFoundError,
    ResumeNotFoundError,
    ResumeVersionConflictError,
)
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
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

    async def update(self, job: Job) -> None:
        if job.id not in self._by_id:
            raise JobNotFoundError(str(job.id))
        previous = self._by_id[job.id]
        old_key = (previous.source.value, previous.external_id)
        new_key = (job.source.value, job.external_id)
        if old_key != new_key:
            if new_key in self._by_source:
                raise JobAlreadyExistsError(job.source.value, job.external_id)
            del self._by_source[old_key]
            self._by_source[new_key] = job.id
        self._by_id[job.id] = job


class InMemoryCareerProfileRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, CareerProfile] = {}
        self._by_user: dict[UUID, UUID] = {}

    async def add(self, profile: CareerProfile) -> None:
        if profile.user_id in self._by_user:
            raise CareerProfileAlreadyExistsError(str(profile.user_id))
        self._by_id[profile.id] = profile
        self._by_user[profile.user_id] = profile.id

    async def get_by_user_id(self, user_id: UUID) -> CareerProfile | None:
        profile_id = self._by_user.get(user_id)
        if profile_id is None:
            return None
        return self._by_id.get(profile_id)

    async def update(self, profile: CareerProfile) -> None:
        if profile.id not in self._by_id:
            raise CareerProfileNotFoundError(str(profile.user_id))
        self._by_id[profile.id] = profile
        self._by_user[profile.user_id] = profile.id


class InMemoryResumeRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Resume] = {}

    async def add(self, resume: Resume) -> None:
        for existing in self._by_id.values():
            if existing.user_id == resume.user_id and existing.version == resume.version:
                raise ResumeVersionConflictError(str(resume.user_id), resume.version)
        self._by_id[resume.id] = resume

    async def get_by_id(self, resume_id: UUID) -> Resume | None:
        return self._by_id.get(resume_id)

    async def get_by_user_and_version(self, user_id: UUID, version: int) -> Resume | None:
        for resume in self._by_id.values():
            if resume.user_id == user_id and resume.version == version:
                return resume
        return None

    async def get_active_by_user_id(self, user_id: UUID) -> Resume | None:
        for resume in self._by_id.values():
            if resume.user_id == user_id and resume.is_active:
                return resume
        return None

    async def list_by_user_id(self, user_id: UUID) -> tuple[Resume, ...]:
        items = [resume for resume in self._by_id.values() if resume.user_id == user_id]
        items.sort(key=lambda item: item.version)
        return tuple(items)

    async def latest_version_number(self, user_id: UUID) -> int | None:
        versions = [resume.version for resume in self._by_id.values() if resume.user_id == user_id]
        return max(versions) if versions else None

    async def set_active(self, user_id: UUID, resume_id: UUID) -> None:
        target = self._by_id.get(resume_id)
        if target is None or target.user_id != user_id:
            raise ResumeNotFoundError(f"Resume {resume_id} was not found for user {user_id}.")
        for resume in self._by_id.values():
            if resume.user_id == user_id:
                resume.is_active = resume.id == resume_id

