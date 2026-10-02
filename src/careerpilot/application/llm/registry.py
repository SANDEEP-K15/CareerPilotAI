from __future__ import annotations

from collections.abc import Iterable

from careerpilot.application.llm.errors import (
    DuplicateLlmProviderRegistrationError,
    UnknownLlmProviderError,
)
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.llm import LlmPort


class LlmProviderRegistry:
    """In-process catalog of LlmPort implementations.

    No vendor adapters are built in. An empty registry is valid until wired.
    """

    def __init__(self, providers: Iterable[LlmPort] = ()) -> None:
        self._providers: dict[str, LlmPort] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: LlmPort) -> None:
        key = provider.provider_key.value
        if key in self._providers:
            raise DuplicateLlmProviderRegistrationError(key)
        self._providers[key] = provider

    def get(self, provider: str | LlmProviderKey) -> LlmPort:
        key = (
            provider.value
            if isinstance(provider, LlmProviderKey)
            else LlmProviderKey.parse(provider).value
        )
        try:
            return self._providers[key]
        except KeyError:
            raise UnknownLlmProviderError(key) from None

    def all(self) -> tuple[LlmPort, ...]:
        return tuple(self._providers[key] for key in sorted(self._providers))

    def keys(self) -> tuple[LlmProviderKey, ...]:
        return tuple(port.provider_key for port in self.all())
