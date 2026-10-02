"""Provider-neutral LLM contracts. Vendor SDKs stay in infrastructure adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey


class LlmRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LlmErrorCode(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    INVALID_REQUEST = "invalid_request"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


class LlmError(Exception):
    """Normalized adapter failure. Never wrap a vendor exception type."""

    def __init__(
        self,
        message: str,
        *,
        code: LlmErrorCode,
        provider: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.provider = provider
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: LlmRole
    content: str


@dataclass(frozen=True, slots=True)
class LlmReportedCost:
    """Actual cost when the provider reports it. Never fabricate amounts."""

    amount: Decimal
    currency: str
    reported_by_provider: bool = True


@dataclass(frozen=True, slots=True)
class LlmUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    provider_request_id: str | None = None
    reported_cost: LlmReportedCost | None = None


@dataclass(frozen=True, slots=True)
class LlmRequest:
    model: LlmModelId
    messages: tuple[LlmMessage, ...]
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LlmResponse:
    content: str
    model: LlmModelId
    usage: LlmUsage
    finish_reason: str | None = None


class LlmPort(Protocol):
    @property
    def provider_key(self) -> LlmProviderKey: ...

    async def complete(self, request: LlmRequest) -> LlmResponse:
        """Run one completion. Raise LlmError for expected failures."""
        ...


def normalize_llm_failure(provider: str, exc: BaseException) -> LlmError:
    """Map generic failures to LlmError. Idempotent for LlmError."""
    if isinstance(exc, LlmError):
        return exc
    if isinstance(exc, TimeoutError):
        return LlmError(
            "LLM provider timed out.",
            code=LlmErrorCode.TIMEOUT,
            provider=provider,
            retryable=True,
        )
    if isinstance(exc, ConnectionError | OSError):
        return LlmError(
            "LLM provider is unavailable.",
            code=LlmErrorCode.UNAVAILABLE,
            provider=provider,
            retryable=True,
        )
    return LlmError(
        "LLM provider failed.",
        code=LlmErrorCode.UNKNOWN,
        provider=provider,
        retryable=False,
    )
