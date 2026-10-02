from __future__ import annotations

import base64
from dataclasses import dataclass, field
from uuid import uuid4

from careerpilot.domain.value_objects.browser_provider_key import BrowserProviderKey
from careerpilot.ports.browser import (
    BrowserArtifact,
    BrowserArtifactKind,
    BrowserElementDescriptor,
    BrowserElementRef,
    BrowserError,
    BrowserErrorCode,
    BrowserInteractionKind,
    BrowserInteractionResult,
    BrowserNavigationResult,
    BrowserPageSnapshot,
    BrowserSessionOptions,
    BrowserSessionPort,
    validate_field_value,
    validate_navigation_url,
)


@dataclass(frozen=True, slots=True)
class FakePage:
    url: str
    title: str
    visible_text: str
    elements: tuple[BrowserElementDescriptor, ...] = ()
    http_status: int = 200


@dataclass
class FakeBrowserSession:
    provider: str
    pages: dict[str, FakePage]
    fail_with: BaseException | None = None
    closed: bool = False
    current_url: str | None = None
    session_id: str = field(default_factory=lambda: f"fake-{uuid4()}")
    filled: dict[str, str] = field(default_factory=dict)
    clicked: set[str] = field(default_factory=set)

    async def navigate(
        self,
        url: str,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserNavigationResult:
        del timeout_seconds
        self._ensure_open()
        if self.fail_with is not None:
            raise self.fail_with
        target = validate_navigation_url(url)
        page = self.pages.get(target)
        if page is None:
            raise BrowserError(
                f"No scripted page for {target}.",
                code=BrowserErrorCode.NAVIGATION_FAILED,
                provider=self.provider,
                retryable=False,
            )
        self.current_url = page.url
        return BrowserNavigationResult(
            requested_url=target,
            final_url=page.url,
            title=page.title,
            http_status=page.http_status,
        )

    async def inspect_page(self) -> BrowserPageSnapshot:
        self._ensure_open()
        if self.current_url is None:
            raise BrowserError(
                "No page loaded.",
                code=BrowserErrorCode.INVALID_COMMAND,
                provider=self.provider,
                retryable=False,
            )
        page = self.pages[self.current_url]
        return BrowserPageSnapshot(
            url=page.url,
            title=page.title,
            visible_text=page.visible_text,
            elements=page.elements,
        )

    async def fill_field(
        self,
        element: BrowserElementRef,
        value: str,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserInteractionResult:
        del timeout_seconds
        self._ensure_open()
        await self._require_element(element)
        self.filled[element.value] = validate_field_value(value)
        return BrowserInteractionResult(
            action=BrowserInteractionKind.FILL,
            element=element,
        )

    async def click(
        self,
        element: BrowserElementRef,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserInteractionResult:
        del timeout_seconds
        self._ensure_open()
        await self._require_element(element)
        self.clicked.add(element.value)
        return BrowserInteractionResult(
            action=BrowserInteractionKind.CLICK,
            element=element,
        )

    async def capture_screenshot(
        self,
        *,
        timeout_seconds: float | None = None,
    ) -> BrowserArtifact:
        del timeout_seconds
        self._ensure_open()
        payload = base64.b64encode(b"fake-screenshot-bytes").decode("ascii")
        return BrowserArtifact(
            kind=BrowserArtifactKind.SCREENSHOT,
            content_type="image/png",
            data_base64=payload,
            metadata={"session_id": self.session_id},
        )

    async def close(self) -> None:
        self.closed = True

    def _ensure_open(self) -> None:
        if self.closed:
            raise BrowserError(
                "Session is closed.",
                code=BrowserErrorCode.SESSION_CLOSED,
                provider=self.provider,
                retryable=False,
            )

    async def _require_element(self, element: BrowserElementRef) -> None:
        if self.current_url is None:
            raise BrowserError(
                "No page loaded.",
                code=BrowserErrorCode.INVALID_COMMAND,
                provider=self.provider,
                retryable=False,
            )
        page = self.pages[self.current_url]
        refs = {item.ref.value for item in page.elements}
        if element.value not in refs:
            raise BrowserError(
                f"Element {element.value} was not found.",
                code=BrowserErrorCode.ELEMENT_NOT_FOUND,
                provider=self.provider,
                retryable=False,
            )


class FakeBrowserAutomationPort:
    """In-memory BrowserAutomationPort for tests. Never launches a real browser."""

    def __init__(
        self,
        name: str = "fake",
        *,
        pages: dict[str, FakePage] | None = None,
        fail_on_open: BaseException | None = None,
        fail_on_navigate: BaseException | None = None,
    ) -> None:
        self._key = BrowserProviderKey.parse(name)
        self._pages = pages or {}
        self._fail_on_open = fail_on_open
        self._fail_on_navigate = fail_on_navigate
        self.last_session: FakeBrowserSession | None = None

    @property
    def provider_key(self) -> BrowserProviderKey:
        return self._key

    async def open_session(
        self,
        options: BrowserSessionOptions | None = None,
    ) -> BrowserSessionPort:
        del options
        if self._fail_on_open is not None:
            raise self._fail_on_open
        session = FakeBrowserSession(
            provider=self._key.value,
            pages=dict(self._pages),
            fail_with=self._fail_on_navigate,
        )
        self.last_session = session
        return session
