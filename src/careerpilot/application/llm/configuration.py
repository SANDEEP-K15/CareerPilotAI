from __future__ import annotations

from dataclasses import dataclass

from careerpilot.application.llm.errors import LlmConfigurationError
from careerpilot.config.settings import LlmSettings
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey


@dataclass(frozen=True, slots=True)
class LlmRuntimeConfiguration:
    """Resolved LLM defaults from environment settings."""

    default_provider: LlmProviderKey | None = None
    default_model: LlmModelId | None = None

    @classmethod
    def from_settings(cls, settings: LlmSettings) -> LlmRuntimeConfiguration:
        provider: LlmProviderKey | None = None
        if settings.provider:
            trimmed = settings.provider.strip()
            if trimmed:
                provider = LlmProviderKey.parse(trimmed)
        model: LlmModelId | None = None
        if settings.default_model:
            trimmed = settings.default_model.strip()
            if trimmed:
                model = LlmModelId.parse(trimmed)
        return cls(default_provider=provider, default_model=model)

    def require_default_provider(self) -> LlmProviderKey:
        if self.default_provider is None:
            raise LlmConfigurationError(
                "LLM__PROVIDER is not configured and no provider was specified."
            )
        return self.default_provider

    def require_default_model(self) -> LlmModelId:
        if self.default_model is None:
            raise LlmConfigurationError(
                "LLM__DEFAULT_MODEL is not configured and no model was specified."
            )
        return self.default_model
