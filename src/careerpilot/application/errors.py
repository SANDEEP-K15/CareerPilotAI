"""Application errors. Machine-readable ``code`` values; no internal traces."""

from __future__ import annotations


class ApplicationError(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class UserNotFoundError(ApplicationError):
    def __init__(self, user_id: str) -> None:
        super().__init__(f"User {user_id} was not found.", code="user_not_found")
        self.user_id = user_id


class JobNotFoundError(ApplicationError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job {job_id} was not found.", code="job_not_found")
        self.job_id = job_id


class JobAlreadyExistsError(ApplicationError):
    def __init__(self, source: str, external_id: str) -> None:
        super().__init__(
            f"Job {source}/{external_id} already exists.",
            code="job_already_exists",
        )
        self.source = source
        self.external_id = external_id
