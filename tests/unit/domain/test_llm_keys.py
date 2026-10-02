from __future__ import annotations

import pytest

from careerpilot.domain.errors import InvalidLlmModelError, InvalidLlmProviderError
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey


def test_llm_provider_key_normalizes() -> None:
    key = LlmProviderKey.parse("Primary-Backend")
    assert key.value == "primary_backend"


def test_llm_provider_key_rejects_invalid() -> None:
    with pytest.raises(InvalidLlmProviderError):
        LlmProviderKey.parse("")


def test_llm_model_id_trims() -> None:
    model = LlmModelId.parse("  demo-model-v1  ")
    assert model.value == "demo-model-v1"


def test_llm_model_id_rejects_empty() -> None:
    with pytest.raises(InvalidLlmModelError):
        LlmModelId.parse("   ")
