from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.application.errors import (
    ApplicationError,
    ApprovalRequestNotFoundError,
    CareerProfileAlreadyExistsError,
    CareerProfileNotFoundError,
    JobAlreadyExistsError,
    JobNotFoundError,
    ResumeNotFoundError,
    ResumeVersionConflictError,
)
from careerpilot.domain.entities.approval_request import ApprovalRequest
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.daily_discovery import DailyDiscovery
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.approval_action import ApprovalAction
from careerpilot.domain.value_objects.approval_status import ApprovalStatus
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.persistence.postgres.mapping import (
    apply_job_to_model,
    apply_profile_to_model,
    approval_request_from_model,
    approval_request_to_model,
    discovery_from_model,
    discovery_to_model,
    job_from_model,
    job_to_model,
    profile_from_model,
    profile_to_model,
    resume_from_model,
    resume_to_model,
    user_from_model,
    user_to_model,
)
from careerpilot.infrastructure.persistence.postgres.models import (
    ApprovalRequestModel,
    CareerProfileModel,
    DailyDiscoveryModel,
    JobModel,
    ResumeModel,
    UserModel,
)


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

    async def list_active(self) -> tuple[Job, ...]:
        stmt = (
            select(JobModel)
            .where(JobModel.status == JobStatus.ACTIVE.value)
            .order_by(JobModel.id)
        )
        result = await self._session.execute(stmt)
        return tuple(job_from_model(row) for row in result.scalars().all())


class SqlAlchemyCareerProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, profile: CareerProfile) -> None:
        self._session.add(profile_to_model(profile))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise CareerProfileAlreadyExistsError(str(profile.user_id)) from exc

    async def get_by_user_id(self, user_id: UUID) -> CareerProfile | None:
        stmt = select(CareerProfileModel).where(CareerProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return profile_from_model(row) if row is not None else None

    async def update(self, profile: CareerProfile) -> None:
        row = await self._session.get(CareerProfileModel, profile.id)
        if row is None:
            raise CareerProfileNotFoundError(str(profile.user_id))
        apply_profile_to_model(profile, row)
        await self._session.flush()


class SqlAlchemyResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, resume: Resume) -> None:
        self._session.add(resume_to_model(resume))
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ResumeVersionConflictError(str(resume.user_id), resume.version) from exc

    async def get_by_id(self, resume_id: UUID) -> Resume | None:
        row = await self._session.get(ResumeModel, resume_id)
        return resume_from_model(row) if row is not None else None

    async def get_by_user_and_version(self, user_id: UUID, version: int) -> Resume | None:
        stmt = select(ResumeModel).where(
            ResumeModel.user_id == user_id,
            ResumeModel.version == version,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return resume_from_model(row) if row is not None else None

    async def get_active_by_user_id(self, user_id: UUID) -> Resume | None:
        stmt = select(ResumeModel).where(
            ResumeModel.user_id == user_id,
            ResumeModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return resume_from_model(row) if row is not None else None

    async def list_by_user_id(self, user_id: UUID) -> tuple[Resume, ...]:
        stmt = (
            select(ResumeModel)
            .where(ResumeModel.user_id == user_id)
            .order_by(ResumeModel.version)
        )
        result = await self._session.execute(stmt)
        return tuple(resume_from_model(row) for row in result.scalars().all())

    async def latest_version_number(self, user_id: UUID) -> int | None:
        stmt = select(func.max(ResumeModel.version)).where(ResumeModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def set_active(self, user_id: UUID, resume_id: UUID) -> None:
        target = await self._session.get(ResumeModel, resume_id)
        if target is None or target.user_id != user_id:
            raise ResumeNotFoundError(f"Resume {resume_id} was not found for user {user_id}.")
        await self._session.execute(
            update(ResumeModel).where(ResumeModel.user_id == user_id).values(is_active=False)
        )
        target.is_active = True
        await self._session.flush()


class SqlAlchemyDailyDiscoveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_and_run(self, user_id: UUID, run_on: date) -> DailyDiscovery | None:
        stmt = select(DailyDiscoveryModel).where(
            DailyDiscoveryModel.user_id == user_id,
            DailyDiscoveryModel.run_on == run_on,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return discovery_from_model(row) if row is not None else None

    async def save(self, discovery: DailyDiscovery) -> DailyDiscovery:
        row = discovery_to_model(discovery)
        stmt = (
            pg_insert(DailyDiscoveryModel)
            .values(
                id=row.id,
                user_id=row.user_id,
                profile_id=row.profile_id,
                run_on=row.run_on,
                threshold=row.threshold,
                selection_limit=row.selection_limit,
                considered=row.considered,
                rejected=row.rejected,
                selections=row.selections,
                source_failures=row.source_failures,
                explanation=row.explanation,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            .on_conflict_do_nothing(constraint="uq_daily_discoveries_user_run")
        )
        await self._session.execute(stmt)
        await self._session.flush()
        stored = await self.get_by_user_and_run(discovery.user_id, discovery.run_on)
        if stored is None:
            raise ApplicationError(
                "Daily discovery was not stored.",
                code="discovery_not_persisted",
            )
        return stored


class SqlAlchemyApprovalRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, request: ApprovalRequest) -> None:
        row = approval_request_to_model(request)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ApplicationError(
                "Approval request could not be stored.",
                code="approval_request_conflict",
            ) from exc

    async def update(self, request: ApprovalRequest) -> None:
        row = await self._session.get(ApprovalRequestModel, request.id)
        if row is None:
            raise ApprovalRequestNotFoundError(str(request.id))
        updated = approval_request_to_model(request)
        row.status = updated.status
        row.reason = updated.reason
        row.decision_note = updated.decision_note
        row.expires_at = updated.expires_at
        row.decided_at = updated.decided_at
        row.updated_at = updated.updated_at
        await self._session.flush()

    async def get_by_id(self, request_id: UUID) -> ApprovalRequest | None:
        row = await self._session.get(ApprovalRequestModel, request_id)
        return approval_request_from_model(row) if row is not None else None

    async def get_for_user(self, user_id: UUID, request_id: UUID) -> ApprovalRequest | None:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.id == request_id,
            ApprovalRequestModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return approval_request_from_model(row) if row is not None else None

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        status: ApprovalStatus | None = None,
        limit: int = 50,
    ) -> tuple[ApprovalRequest, ...]:
        stmt = (
            select(ApprovalRequestModel)
            .where(ApprovalRequestModel.user_id == user_id)
            .order_by(ApprovalRequestModel.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(ApprovalRequestModel.status == status.value)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(approval_request_from_model(row) for row in rows)

    async def list_pending_for(
        self,
        user_id: UUID,
        job_id: UUID,
        action: ApprovalAction,
    ) -> tuple[ApprovalRequest, ...]:
        stmt = select(ApprovalRequestModel).where(
            ApprovalRequestModel.user_id == user_id,
            ApprovalRequestModel.job_id == job_id,
            ApprovalRequestModel.action == action.value,
            ApprovalRequestModel.status == ApprovalStatus.PENDING.value,
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return tuple(approval_request_from_model(row) for row in rows)
