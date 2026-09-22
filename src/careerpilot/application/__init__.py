"""Use cases depend on ports only. Provider-neutral."""

from careerpilot.application.errors import (
    ApplicationError,
    JobAlreadyExistsError,
    JobNotFoundError,
    UserNotFoundError,
)
from careerpilot.application.job_sources import (
    DuplicateJobSourceRegistrationError,
    JobSourceRegistry,
    SearchRegisteredSourcesUseCase,
    UnknownJobSourceError,
)
from careerpilot.application.jobs import IngestOutcome, IngestRawJobResult, job_from_raw
from careerpilot.application.use_cases.get_job import GetJobUseCase
from careerpilot.application.use_cases.get_user import GetUserUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.persist_job import PersistJobCommand, PersistJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase

__all__ = [
    "ApplicationError",
    "DuplicateJobSourceRegistrationError",
    "GetJobUseCase",
    "GetUserUseCase",
    "IngestOutcome",
    "IngestRawJobResult",
    "IngestRawJobUseCase",
    "JobAlreadyExistsError",
    "JobNotFoundError",
    "JobSourceRegistry",
    "PersistJobCommand",
    "PersistJobUseCase",
    "RegisterUserCommand",
    "RegisterUserUseCase",
    "SearchRegisteredSourcesUseCase",
    "UnknownJobSourceError",
    "UserNotFoundError",
    "job_from_raw",
]
