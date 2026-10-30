"""LLM provider adapters.

Vendor SDKs are imported only here. Providers are built from LlmSettings by the
composition root; none are registered implicitly.
"""

from __future__ import annotations

from careerpilot.config.settings import LlmSettings
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.infrastructure.llm.anthropic_provider import (
    ANTHROPIC_PROVIDER_KEY,
    AnthropicLlmProvider,
)
from careerpilot.ports.llm import LlmPort

__all__ = ["AnthropicLlmProvider", "llm_providers_from_settings"]


def llm_providers_from_settings(settings: LlmSettings) -> tuple[LlmPort, ...]:
    """Build the configured provider, or none when LLM__PROVIDER is unset."""
    if settings.provider is None:
        return ()
    key = LlmProviderKey.parse(settings.provider)
    if key == ANTHROPIC_PROVIDER_KEY:
        if settings.api_key is None or not settings.api_key.get_secret_value():
            raise ValueError("LLM__API_KEY is required when LLM__PROVIDER=anthropic.")
        return (AnthropicLlmProvider(api_key=settings.api_key.get_secret_value()),)
    raise ValueError(f"Unsupported LLM provider '{key.value}'. Supported: anthropic.")
