"""BrowserAutomationPort contract tests against the in-memory fake."""

from __future__ import annotations

import pytest

from careerpilot.ports.browser import (
    BrowserArtifactKind,
    BrowserElementDescriptor,
    BrowserElementRef,
    BrowserError,
    BrowserErrorCode,
    BrowserInteractionKind,
    normalize_browser_failure,
    validate_navigation_url,
)
from tests.fakes.browser import FakeBrowserAutomationPort, FakePage


def _page() -> FakePage:
    return FakePage(
        url="https://example.com/apply",
        title="Apply",
        visible_text="Submit your application",
        elements=(
            BrowserElementDescriptor(
                ref=BrowserElementRef("email"),
                label="Email",
                role="textbox",
            ),
        ),
    )


async def test_fake_session_navigates_and_inspects() -> None:
    port = FakeBrowserAutomationPort(
        "lab",
        pages={"https://example.com/apply": _page()},
    )
    session = await port.open_session()
    try:
        nav = await session.navigate("https://example.com/apply")
        assert nav.title == "Apply"
        page = await session.inspect_page()
        assert page.elements[0].ref.value == "email"
        shot = await session.capture_screenshot()
        assert shot.kind is BrowserArtifactKind.SCREENSHOT
    finally:
        await session.close()


async def test_fake_session_supports_form_interaction() -> None:
    port = FakeBrowserAutomationPort(
        "lab",
        pages={"https://example.com/apply": _page()},
    )
    session = await port.open_session()
    try:
        await session.navigate("https://example.com/apply")
        fill = await session.fill_field(BrowserElementRef("email"), "ada@example.com")
        assert fill.action is BrowserInteractionKind.FILL
        click = await session.click(BrowserElementRef("email"))
        assert click.action is BrowserInteractionKind.CLICK
        assert port.last_session is not None
        assert port.last_session.filled["email"] == "ada@example.com"
    finally:
        await session.close()


async def test_navigation_failure_is_structured() -> None:
    port = FakeBrowserAutomationPort("lab", pages={})
    session = await port.open_session()
    try:
        with pytest.raises(BrowserError) as exc:
            await session.navigate("https://example.com/missing")
        assert exc.value.code is BrowserErrorCode.NAVIGATION_FAILED
        assert exc.value.retryable is False
    finally:
        await session.close()


async def test_closed_session_rejects_commands() -> None:
    port = FakeBrowserAutomationPort("lab", pages={"https://example.com/apply": _page()})
    session = await port.open_session()
    await session.close()
    with pytest.raises(BrowserError) as exc:
        await session.navigate("https://example.com/apply")
    assert exc.value.code is BrowserErrorCode.SESSION_CLOSED


async def test_normalize_browser_failure_maps_timeout() -> None:
    error = normalize_browser_failure("lab", TimeoutError())
    assert error.code is BrowserErrorCode.TIMEOUT
    assert error.retryable is True


def test_validate_navigation_url_rejects_invalid_scheme() -> None:
    with pytest.raises(BrowserError) as exc:
        validate_navigation_url("ftp://example.com")
    assert exc.value.code is BrowserErrorCode.INVALID_COMMAND
