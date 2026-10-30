"""AnthropicLlmProvider against the real SDK client over an in-memory transport.

No network access and no API key.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2
import pytest
from pydantic import SecretStr

from careerpilot.config.settings import LlmSettings
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.infrastructure.llm import AnthropicLlmProvider, llm_providers_from_settings
from careerpilot.ports.llm import LlmError, LlmErrorCode, LlmMessage, LlmRequest, LlmRole

Handler = Callable[[httpx2.Request], httpx2.Response]


def _message(text: str = "Strong match: Python and FastAPI.", **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": "msg_test_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-5-5",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 120, "output_tokens": 30},
    }
    body.update(overrides)
    return body


def _provider(handler: Handler) -> tuple[AnthropicLlmProvider, list[httpx2.Request]]:
    seen: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    client = anthropic.AsyncAnthropic(
        api_key="test-key-not-real",
        max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(record)),
    )
    return AnthropicLlmProvider(client=client), seen


def _request(model: str = "claude-opus-5-5", **kwargs: Any) -> LlmRequest:
    return LlmRequest(
        model=LlmModelId.parse(model),
        messages=(
            LlmMessage(role=LlmRole.SYSTEM, content="You rank job matches."),
            LlmMessage(role=LlmRole.USER, content="Rate this job for a Python backend engineer."),
        ),
        **kwargs,
    )


async def test_completion_maps_text_usage_and_request_id() -> None:
    provider, _ = _provider(lambda _: httpx2.Response(200, json=_message()))
    response = await provider.complete(_request())

    assert response.content == "Strong match: Python and FastAPI."
    assert response.model.value == "claude-opus-5-5"
    assert response.finish_reason == "end_turn"
    assert response.usage.prompt_tokens == 120
    assert response.usage.completion_tokens == 30
    assert response.usage.total_tokens == 150
    assert response.usage.provider_request_id == "msg_test_1"
    assert response.usage.reported_cost is None  # never fabricated


async def test_wire_request_shape() -> None:
    provider, seen = _provider(lambda _: httpx2.Response(200, json=_message()))
    await provider.complete(_request(temperature=0.2, max_output_tokens=500))

    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/messages"
    assert body["model"] == "claude-opus-5-5"
    assert body["max_tokens"] == 500
    assert body["system"] == "You rank job matches."
    assert body["messages"] == [
        {"role": "user", "content": "Rate this job for a Python backend engineer."}
    ]
    assert "temperature" not in body  # sampling parameters are rejected by current models
    assert body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in seen[0].headers["anthropic-beta"]


async def test_models_without_fallback_support_omit_the_parameter() -> None:
    haiku = _message(model="claude-haiku-5-5")
    provider, seen = _provider(lambda _: httpx2.Response(200, json=haiku))
    response = await provider.complete(_request(model="claude-haiku-5-5"))

    body = json.loads(seen[0].content)
    assert "fallbacks" not in body
    assert "anthropic-beta" not in seen[0].headers
    assert body["max_tokens"] == 16_000
    assert response.model.value == "claude-haiku-5-5"


async def test_reports_the_model_that_served_a_fallback() -> None:
    provider, _ = _provider(lambda _: httpx2.Response(200, json=_message(model="claude-opus-4-8")))
    response = await provider.complete(_request())
    assert response.model.value == "claude-opus-4-8"


async def test_refusal_becomes_content_filter_error() -> None:
    provider, _ = _provider(
        lambda _: httpx2.Response(200, json=_message(text="", content=[], stop_reason="refusal"))
    )
    with pytest.raises(LlmError) as exc:
        await provider.complete(_request())
    assert exc.value.code is LlmErrorCode.CONTENT_FILTER
    assert exc.value.retryable is False


@pytest.mark.parametrize(
    ("status", "code", "retryable"),
    [
        (400, LlmErrorCode.INVALID_REQUEST, False),
        (401, LlmErrorCode.UNAUTHORIZED, False),
        (403, LlmErrorCode.UNAUTHORIZED, False),
        (404, LlmErrorCode.INVALID_REQUEST, False),
        (429, LlmErrorCode.RATE_LIMITED, True),
        (500, LlmErrorCode.UNAVAILABLE, True),
        (529, LlmErrorCode.UNAVAILABLE, True),
    ],
)
async def test_http_errors_are_normalized(status: int, code: LlmErrorCode, retryable: bool) -> None:
    secret_echo = "user resume text that must not leak"
    provider, _ = _provider(
        lambda _: httpx2.Response(
            status, json={"type": "error", "error": {"type": "x", "message": secret_echo}}
        )
    )
    with pytest.raises(LlmError) as exc:
        await provider.complete(_request())
    assert exc.value.code is code
    assert exc.value.retryable is retryable
    assert exc.value.provider == "anthropic"
    assert secret_echo not in exc.value.message
    assert exc.value.__cause__ is None  # vendor exception is not chained


async def test_connection_failure_is_unavailable() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("connection refused", request=request)

    provider, _ = _provider(fail)
    with pytest.raises(LlmError) as exc:
        await provider.complete(_request())
    assert exc.value.code is LlmErrorCode.UNAVAILABLE
    assert exc.value.retryable is True


async def test_timeout_is_retryable_timeout() -> None:
    def slow(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("timed out", request=request)

    provider, _ = _provider(slow)
    with pytest.raises(LlmError) as exc:
        await provider.complete(_request())
    assert exc.value.code is LlmErrorCode.TIMEOUT


async def test_empty_text_is_an_error_not_an_empty_answer() -> None:
    provider, _ = _provider(lambda _: httpx2.Response(200, json=_message(content=[])))
    with pytest.raises(LlmError) as exc:
        await provider.complete(_request())
    assert exc.value.code is LlmErrorCode.UNKNOWN


async def test_system_only_request_is_rejected_before_calling_the_api() -> None:
    provider, seen = _provider(lambda _: httpx2.Response(200, json=_message()))
    request = LlmRequest(
        model=LlmModelId.parse("claude-opus-5-5"),
        messages=(LlmMessage(role=LlmRole.SYSTEM, content="only system"),),
    )
    with pytest.raises(LlmError) as exc:
        await provider.complete(request)
    assert exc.value.code is LlmErrorCode.INVALID_REQUEST
    assert seen == []


def test_requires_an_api_key_when_no_client_is_injected() -> None:
    with pytest.raises(ValueError, match="API key"):
        AnthropicLlmProvider()


def test_settings_factory() -> None:
    assert llm_providers_from_settings(LlmSettings()) == ()

    (provider,) = llm_providers_from_settings(
        LlmSettings(provider="anthropic", api_key=SecretStr("test-key-not-real"))
    )
    assert provider.provider_key.value == "anthropic"

    with pytest.raises(ValueError, match="LLM__API_KEY"):
        llm_providers_from_settings(LlmSettings(provider="anthropic"))
    with pytest.raises(ValueError, match="Unsupported"):
        llm_providers_from_settings(LlmSettings(provider="primary", api_key=SecretStr("k")))
