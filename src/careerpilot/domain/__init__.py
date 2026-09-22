"""Canonical domain types. No infrastructure imports."""

from careerpilot.domain.content_hash import job_content_hash
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume, ResumeContentType
from careerpilot.domain.entities.user import User
from careerpilot.domain.errors import (
    DomainError,
    InvalidJobError,
    InvalidProfileError,
    InvalidResumeError,
    InvalidUserError,
)
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.domain.value_objects.user_status import UserStatus

__all__ = [
    "CareerProfile",
    "DomainError",
    "EmploymentType",
    "InvalidJobError",
    "InvalidProfileError",
    "InvalidResumeError",
    "InvalidUserError",
    "Job",
    "JobStatus",
    "RemotePolicy",
    "Resume",
    "ResumeContentType",
    "SourceKey",
    "User",
    "UserStatus",
    "job_content_hash",
]
