from __future__ import annotations

import pytest
from tests.fakes.llm import FakeLlmProvider

from careerpilot.application.llm import (
    DuplicateLlmProviderRegistrationError,
    LlmProviderRegistry,
    UnknownLlmProviderError,
)


def test_empty_llm_registry_is_valid() -> None:
    registry = LlmProviderRegistry()
    assert registry.all() == ()


def test_register_and_lookup_llm_provider() -> None:
    first = FakeLlmProvider("alpha")
    second = FakeLlmProvider("beta")
    registry = LlmProviderRegistry((first,))
    registry.register(second)
    assert registry.get("alpha") is first
    assert registry.get(second.provider_key) is second
    assert registry.keys() == (first.provider_key, second.provider_key)


def test_duplicate_llm_provider_registration_is_rejected() -> None:
    registry = LlmProviderRegistry((FakeLlmProvider("alpha"),))
    with pytest.raises(DuplicateLlmProviderRegistrationError) as exc:
        registry.register(FakeLlmProvider("alpha"))
    assert exc.value.code == "duplicate_llm_provider"


def test_unknown_llm_provider_is_rejected() -> None:
    registry = LlmProviderRegistry()
    with pytest.raises(UnknownLlmProviderError) as exc:
        registry.get("missing")
    assert exc.value.code == "unknown_llm_provider"


def test_registry_has_no_built_in_providers() -> None:
    registry = LlmProviderRegistry()
    with pytest.raises(UnknownLlmProviderError):
        registry.get("primary")
