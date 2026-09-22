from __future__ import annotations

from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.domain.value_objects.user_status import UserStatus
from careerpilot.infrastructure.persistence.postgres.models import JobModel, UserModel


def user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        display_name=user.display_name,
        status=user.status.value,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def user_from_model(row: UserModel) -> User:
    return User(
        id=row.id,
        display_name=row.display_name,
        status=UserStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def job_to_model(job: Job) -> JobModel:
    return JobModel(
        id=job.id,
        source=job.source.value,
        external_id=job.external_id,
        title=job.title,
        company_name=job.company_name,
        source_url=job.source_url,
        application_url=job.application_url,
        location=job.location,
        remote_policy=job.remote_policy.value,
        employment_type=job.employment_type.value,
        description=job.description,
        posted_at=job.posted_at,
        discovered_at=job.discovered_at,
        content_hash=job.content_hash,
        extra=dict(job.extra),
        status=job.status.value,
    )


def job_from_model(row: JobModel) -> Job:
    return Job(
        id=row.id,
        source=SourceKey(row.source),
        external_id=row.external_id,
        title=row.title,
        company_name=row.company_name,
        source_url=row.source_url,
        application_url=row.application_url,
        location=row.location,
        remote_policy=RemotePolicy(row.remote_policy),
        employment_type=EmploymentType(row.employment_type),
        description=row.description,
        posted_at=row.posted_at,
        discovered_at=row.discovered_at,
        content_hash=row.content_hash,
        extra=dict(row.extra),
        status=JobStatus(row.status),
    )
