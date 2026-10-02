"""LlmPort contract tests against the in-memory fake."""

from __future__ import annotations

import pytest

from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.ports.llm import LlmError, LlmErrorCode, LlmMessage, LlmRequest, LlmRole
from tests.fakes.llm import CodedLlmFailureProvider, FakeLlmProvider


async def test_fake_provider_returns_structured_response() -> None:
    provider = FakeLlmProvider("lab", response_text="hello world")
    request = LlmRequest(
        model=LlmModelId.parse("demo-model"),
        messages=(LlmMessage(role=LlmRole.USER, content="ping"),),
    )
    response = await provider.complete(request)
    assert response.content == "hello world"
    assert response.usage.prompt_tokens == 1
    assert response.usage.completion_tokens == 2
    assert response.usage.total_tokens == 3
    assert response.usage.reported_cost is None


async def test_fake_provider_can_include_reported_cost_only() -> None:
    provider = FakeLlmProvider("lab", include_reported_cost=True)
    response = await provider.complete(
        LlmRequest(
            model=LlmModelId.parse("demo-model"),
            messages=(LlmMessage(role=LlmRole.USER, content="one two"),),
        )
    )
    assert response.usage.reported_cost is not None
    assert response.usage.reported_cost.reported_by_provider is True


async def test_coded_failure_raises_llm_error() -> None:
    provider = CodedLlmFailureProvider("lab")
    with pytest.raises(LlmError) as exc:
        await provider.complete(
            LlmRequest(
                model=LlmModelId.parse("demo-model"),
                messages=(LlmMessage(role=LlmRole.USER, content="run"),),
            )
        )
    assert exc.value.code is LlmErrorCode.INVALID_REQUEST
