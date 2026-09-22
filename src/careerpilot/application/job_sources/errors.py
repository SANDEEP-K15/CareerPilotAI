from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class DuplicateJobSourceRegistrationError(ApplicationError):
    def __init__(self, source: str) -> None:
        super().__init__(
            f"Job source '{source}' is already registered.",
            code="duplicate_job_source",
        )
        self.source = source


class UnknownJobSourceError(ApplicationError):
    def __init__(self, source: str) -> None:
        super().__init__(
            f"Job source '{source}' is not registered.",
            code="unknown_job_source",
        )
        self.source = source
