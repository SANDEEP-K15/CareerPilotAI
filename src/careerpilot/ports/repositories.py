from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from careerpilot.domain.entities.approval_request import ApprovalRequest
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.daily_discovery import DailyDiscovery
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus
from careerpilot.domain.value_objects.source_key import SourceKey


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...


class JobRepository(Protocol):
    async def add(self, job: Job) -> None: ...

    async def get_by_id(self, job_id: UUID) -> Job | None: ...

    async def get_by_source_identity(self, source: SourceKey, external_id: str) -> Job | None: ...

    async def update(self, job: Job) -> None: ...

    async def list_active(self) -> tuple[Job, ...]: ...


class CareerProfileRepository(Protocol):
    async def add(self, profile: CareerProfile) -> None: ...

    async def get_by_user_id(self, user_id: UUID) -> CareerProfile | None: ...

    async def update(self, profile: CareerProfile) -> None: ...


class ResumeRepository(Protocol):
    async def add(self, resume: Resume) -> None: ...

    async def get_by_id(self, resume_id: UUID) -> Resume | None: ...

    async def get_by_user_and_version(self, user_id: UUID, version: int) -> Resume | None: ...

    async def get_active_by_user_id(self, user_id: UUID) -> Resume | None: ...

    async def list_by_user_id(self, user_id: UUID) -> tuple[Resume, ...]: ...

    async def latest_version_number(self, user_id: UUID) -> int | None: ...

    async def set_active(self, user_id: UUID, resume_id: UUID) -> None: ...


class DailyDiscoveryRepository(Protocol):
    async def get_by_user_and_run(self, user_id: UUID, run_on: date) -> DailyDiscovery | None: ...

    async def save(self, discovery: DailyDiscovery) -> DailyDiscovery: ...


class ApprovalRequestRepository(Protocol):
    async def add(self, request: ApprovalRequest) -> None: ...

    async def update(self, request: ApprovalRequest) -> None: ...

    async def get_by_id(self, request_id: UUID) -> ApprovalRequest | None: ...

    async def get_for_user(self, user_id: UUID, request_id: UUID) -> ApprovalRequest | None: ...

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        status: ApprovalStatus | None = None,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]: ...

    async def list_pending_for(
        self,
        user_id: UUID,
        job_id: UUID,
        action: ApprovalAction,
    ) -> tuple[ApprovalRequest, ...]: ...
