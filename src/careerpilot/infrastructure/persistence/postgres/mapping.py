from __future__ import annotations

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume, ResumeContentType
from careerpilot.domain.entities.user import User
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.domain.value_objects.user_status import UserStatus
from careerpilot.infrastructure.persistence.postgres.models import (
    CareerProfileModel,
    JobModel,
    ResumeModel,
    UserModel,
)


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


def apply_job_to_model(job: Job, row: JobModel) -> None:
    row.source = job.source.value
    row.external_id = job.external_id
    row.title = job.title
    row.company_name = job.company_name
    row.source_url = job.source_url
    row.application_url = job.application_url
    row.location = job.location
    row.remote_policy = job.remote_policy.value
    row.employment_type = job.employment_type.value
    row.description = job.description
    row.posted_at = job.posted_at
    row.discovered_at = job.discovered_at
    row.content_hash = job.content_hash
    row.extra = dict(job.extra)
    row.status = job.status.value


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


def profile_to_model(profile: CareerProfile) -> CareerProfileModel:
    return CareerProfileModel(
        id=profile.id,
        user_id=profile.user_id,
        headline=profile.headline,
        summary=profile.summary,
        skills=list(profile.skills),
        target_titles=list(profile.target_titles),
        locations=list(profile.locations),
        remote_policy=profile.remote_policy.value,
        employment_type=profile.employment_type.value,
        years_experience=profile.years_experience,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def apply_profile_to_model(profile: CareerProfile, row: CareerProfileModel) -> None:
    row.headline = profile.headline
    row.summary = profile.summary
    row.skills = list(profile.skills)
    row.target_titles = list(profile.target_titles)
    row.locations = list(profile.locations)
    row.remote_policy = profile.remote_policy.value
    row.employment_type = profile.employment_type.value
    row.years_experience = profile.years_experience
    row.updated_at = profile.updated_at


def profile_from_model(row: CareerProfileModel) -> CareerProfile:
    return CareerProfile(
        id=row.id,
        user_id=row.user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        headline=row.headline,
        summary=row.summary,
        skills=tuple(str(item) for item in row.skills),
        target_titles=tuple(str(item) for item in row.target_titles),
        locations=tuple(str(item) for item in row.locations),
        remote_policy=RemotePolicy(row.remote_policy),
        employment_type=EmploymentType(row.employment_type),
        years_experience=row.years_experience,
    )


def resume_to_model(resume: Resume) -> ResumeModel:
    return ResumeModel(
        id=resume.id,
        user_id=resume.user_id,
        version=resume.version,
        label=resume.label,
        content=resume.content,
        content_type=resume.content_type.value,
        is_active=resume.is_active,
        created_at=resume.created_at,
    )


def resume_from_model(row: ResumeModel) -> Resume:
    return Resume(
        id=row.id,
        user_id=row.user_id,
        version=row.version,
        content=row.content,
        created_at=row.created_at,
        label=row.label,
        content_type=ResumeContentType(row.content_type),
        is_active=row.is_active,
    )
