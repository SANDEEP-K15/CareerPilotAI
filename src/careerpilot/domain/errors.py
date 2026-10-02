"""Structured domain errors. Safe to surface; no stack traces or secrets."""

from __future__ import annotations


class DomainError(Exception):
    """Base error for invariant violations in the domain model."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidUserError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_user")


class InvalidJobError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_job")


class InvalidProfileError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_profile")


class InvalidResumeError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_resume")


class InvalidApplicationPrepError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_application_prep")


class InvalidApprovalRequestError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_approval_request")


class InvalidAgentError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_agent")


class InvalidLlmProviderError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_llm_provider")


class InvalidLlmModelError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_llm_model")


class InvalidBrowserProviderError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_browser_provider")
