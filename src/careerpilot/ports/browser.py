"""Provider-neutral browser automation contracts.

Vendor-specific browser drivers belong in infrastructure adapters added after M19.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from careerpilot.domain.value_objects.browser_provider_key import BrowserProviderKey

_DEFAULT_TIMEOUT_SECONDS = 30.0
_MAX_URL_LEN = 2048
_MAX_FIELD_VALUE_LEN = 10_000
_MAX_ARTIFACT_BYTES = 5_000_000


class BrowserErrorCode(StrEnum):
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    NAVIGATION_FAILED = "navigation_failed"
    ELEMENT_NOT_FOUND = "element_not_found"
    INVALID_COMMAND = "invalid_command"
    SESSION_CLOSED = "session_closed"
    UNKNOWN = "unknown"


class BrowserArtifactKind(StrEnum):
    SCREENSHOT = "screenshot"
    PAGE_HTML = "page_html"


class BrowserInteractionKind(StrEnum):
    FILL = "fill"
    CLICK = "click"


class BrowserError(Exception):
    """Normalized automation failure. Never wrap a vendor exception type."""

    def __init__(
        self,
        message: str,
        *,
        code: BrowserErrorCode,
        provider: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.provider = provider
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class BrowserSessionOptions:
    default_timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    viewport_width: int = 1280
    viewport_height: int = 720

    def __post_init__(self) -> None:
        if self.default_timeout_seconds <= 0:
            raise BrowserError(
                "default_timeout_seconds must be positive.",
                code=BrowserErrorCode.INVALID_COMMAND,
                provider="browser",
                retryable=False,
            )


@dataclass(frozen=True, slots=True)
class BrowserElementRef:
    """Opaque element handle within the current page."""

    value: str

    def __post_init__(self) -> None:
        trimmed = self.value.strip()
        if not trimmed:
            raise BrowserError(
                "element ref must not be empty.",
                code=BrowserErrorCode.INVALID_COMMAND,
                provider="browser",
                retryable=False,
            )
        object.__setattr__(self, "value", trimmed)


@dataclass(frozen=True, slots=True)
class BrowserElementDescriptor:
    ref: BrowserElementRef
    label: str
    role: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserNavigationResult:
    requested_url: str
    final_url: str
    title: str | None = None
    http_status: int | None = None


@dataclass(frozen=True, slots=True)
class BrowserPageSnapshot:
    url: str
    title: str | None
    visible_text: str
    elements: tuple[BrowserElementDescriptor, ...] = ()


@dataclass(frozen=True, slots=True)
class BrowserInteractionResult:
    action: BrowserInteractionKind
    element: BrowserElementRef
    succeeded: bool = True


@dataclass(frozen=True, slots=True)
class BrowserArtifact:
    kind: BrowserArtifactKind
    content_type: str
    data_base64: str
    metadata: dict[str, str] = field(default_factory=dict)


class BrowserSessionPort(Protocol):
    """One browser session. Must be closed explicitly or via context manager."""

    @property
    def session_id(self) -> str: ...

    async def navigate(
        self,
        url: str,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserNavigationResult: ...

    async def inspect_page(self) -> BrowserPageSnapshot: ...

    async def fill_field(
        self,
        element: BrowserElementRef,
        value: str,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserInteractionResult: ...

    async def click(
        self,
        element: BrowserElementRef,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserInteractionResult: ...

    async def capture_screenshot(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserArtifact: ...

    async def close(self) -> None: ...


class BrowserAutomationPort(Protocol):
    """Opens sessions against a concrete automation backend."""

    @property
    def provider_key(self) -> BrowserProviderKey: ...

    async def open_session(
        self,
        options: BrowserSessionOptions | None = None,
    ) -> BrowserSessionPort: ...


def normalize_browser_failure(provider: str, exc: BaseException) -> BrowserError:
    """Map generic failures to BrowserError. Idempotent for BrowserError."""
    if isinstance(exc, BrowserError):
        return exc
    if isinstance(exc, TimeoutError):
        return BrowserError(
            "Browser automation timed out.",
            code=BrowserErrorCode.TIMEOUT,
            provider=provider,
            retryable=True,
        )
    if isinstance(exc, ConnectionError | OSError):
        return BrowserError(
            "Browser automation backend is unavailable.",
            code=BrowserErrorCode.UNAVAILABLE,
            provider=provider,
            retryable=True,
        )
    return BrowserError(
        "Browser automation failed.",
        code=BrowserErrorCode.UNKNOWN,
        provider=provider,
        retryable=False,
    )


def validate_navigation_url(url: str) -> str:
    trimmed = url.strip()
    if not trimmed:
        raise BrowserError(
            "url is required.",
            code=BrowserErrorCode.INVALID_COMMAND,
            provider="browser",
            retryable=False,
        )
    if len(trimmed) > _MAX_URL_LEN:
        raise BrowserError(
            f"url must be at most {_MAX_URL_LEN} characters.",
            code=BrowserErrorCode.INVALID_COMMAND,
            provider="browser",
            retryable=False,
        )
    if not trimmed.startswith(("http://", "https://")):
        raise BrowserError(
            "url must use http or https.",
            code=BrowserErrorCode.INVALID_COMMAND,
            provider="browser",
            retryable=False,
        )
    return trimmed


def validate_field_value(value: str) -> str:
    if len(value) > _MAX_FIELD_VALUE_LEN:
        raise BrowserError(
            f"field value must be at most {_MAX_FIELD_VALUE_LEN} characters.",
            code=BrowserErrorCode.INVALID_COMMAND,
            provider="browser",
            retryable=False,
        )
    return value
