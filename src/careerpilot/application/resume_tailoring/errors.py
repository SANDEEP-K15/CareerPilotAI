from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class ResumeTailoringFailedError(ApplicationError):
    def __init__(self, message: str = "Resume tailoring could not be completed.") -> None:
        super().__init__(message, code="resume_tailoring_failed")
