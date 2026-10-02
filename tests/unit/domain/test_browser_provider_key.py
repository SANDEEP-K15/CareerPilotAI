from __future__ import annotations

import pytest

from careerpilot.domain.errors import InvalidBrowserProviderError
from careerpilot.domain.value_objects.browser_provider_key import BrowserProviderKey


def test_browser_provider_key_parses_and_normalizes() -> None:
    key = BrowserProviderKey.parse("Fake-Lab")
    assert key.value == "fake_lab"


def test_browser_provider_key_rejects_invalid() -> None:
    with pytest.raises(InvalidBrowserProviderError):
        BrowserProviderKey.parse("")
