from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class DuplicateLlmProviderRegistrationError(ApplicationError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' is already registered.",
            code="duplicate_llm_provider",
        )
        self.provider = provider


class UnknownLlmProviderError(ApplicationError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"LLM provider '{provider}' is not registered.",
            code="unknown_llm_provider",
        )
        self.provider = provider


class InvalidLlmInvocationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_llm_invocation")


class LlmConfigurationError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="llm_configuration_error")
