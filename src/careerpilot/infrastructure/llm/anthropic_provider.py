"""LlmPort adapter for Anthropic's Messages API. The vendor SDK stays inside this module."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from careerpilot.domain.errors import InvalidLlmModelError
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.llm import (
    LlmError,
    LlmErrorCode,
    LlmMessage,
    LlmRequest,
    LlmResponse,
    LlmRole,
    LlmUsage,
)

logger = logging.getLogger(__name__)

ANTHROPIC_PROVIDER_KEY = LlmProviderKey.parse("anthropic")
_PROVIDER = ANTHROPIC_PROVIDER_KEY.value

DEFAULT_MAX_OUTPUT_TOKENS = 16_000

# Models that accept server-side refusal fallbacks in "default" routing mode. Other models
# are called without the parameter, so a refusal surfaces as CONTENT_FILTER.
_FALLBACK_MODELS = frozenset(
    {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
)
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def _status_error(status: int) -> LlmError:
    if status in (401, 403):
        code, retryable = LlmErrorCode.UNAUTHORIZED, False
    elif status == 408:
        code, retryable = LlmErrorCode.TIMEOUT, True
    elif status == 429:
        code, retryable = LlmErrorCode.RATE_LIMITED, True
    elif status >= 500:
        code, retryable = LlmErrorCode.UNAVAILABLE, True
    elif 400 <= status < 500:
        code, retryable = LlmErrorCode.INVALID_REQUEST, False
    else:
        code, retryable = LlmErrorCode.UNKNOWN, False
    # The vendor message and body are not propagated: they can echo request content.
    return LlmError(
        f"Anthropic request failed with HTTP {status}.",
        code=code,
        provider=_PROVIDER,
        retryable=retryable,
    )


def _split_messages(messages: tuple[LlmMessage, ...]) -> tuple[str, list[dict[str, str]]]:
    system = "\n\n".join(m.content for m in messages if m.role is LlmRole.SYSTEM)
    turns = [
        {"role": m.role.value, "content": m.content}
        for m in messages
        if m.role is not LlmRole.SYSTEM
    ]
    return system, turns


class AnthropicLlmProvider:
    """Optional LlmPort adapter. Credentials come from configuration; nothing is hardcoded."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        if client is None:
            if not api_key:
                raise ValueError("An Anthropic API key is required to build AnthropicLlmProvider.")
            client = anthropic.AsyncAnthropic(
                api_key=api_key, timeout=timeout_seconds, max_retries=max_retries
            )
        self._client = client

    @property
    def provider_key(self) -> LlmProviderKey:
        return ANTHROPIC_PROVIDER_KEY

    async def complete(self, request: LlmRequest) -> LlmResponse:
        system, turns = _split_messages(request.messages)
        if not turns:
            raise LlmError(
                "At least one user message is required.",
                code=LlmErrorCode.INVALID_REQUEST,
                provider=_PROVIDER,
            )
        # request.temperature is intentionally not sent: current Claude models reject
        # sampling parameters.
        params: dict[str, Any] = {
            "model": request.model.value,
            "max_tokens": request.max_output_tokens or DEFAULT_MAX_OUTPUT_TOKENS,
            "messages": turns,
        }
        if system:
            params["system"] = system
        if request.model.value in _FALLBACK_MODELS:
            params["betas"] = [_FALLBACK_BETA]
            params["fallbacks"] = "default"

        try:
            response = await self._client.beta.messages.create(**params)
        except anthropic.APIStatusError as exc:
            raise _status_error(exc.status_code) from None
        except anthropic.APITimeoutError:
            raise LlmError(
                "Anthropic request timed out.",
                code=LlmErrorCode.TIMEOUT,
                provider=_PROVIDER,
                retryable=True,
            ) from None
        except anthropic.APIConnectionError:
            raise LlmError(
                "Anthropic is unreachable.",
                code=LlmErrorCode.UNAVAILABLE,
                provider=_PROVIDER,
                retryable=True,
            ) from None

        if response.stop_reason == "refusal":
            raise LlmError(
                "The model declined this request.",
                code=LlmErrorCode.CONTENT_FILTER,
                provider=_PROVIDER,
            )

        text = "".join(block.text for block in response.content if block.type == "text")
        if not text:
            raise LlmError(
                "Anthropic returned no text content.",
                code=LlmErrorCode.UNKNOWN,
                provider=_PROVIDER,
            )

        # Report the model that actually served the request (a fallback may have run).
        try:
            served_by = LlmModelId.parse(response.model)
        except InvalidLlmModelError:
            served_by = request.model

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        return LlmResponse(
            content=text,
            model=served_by,
            # Anthropic does not report a monetary cost per request, so reported_cost stays None.
            usage=LlmUsage(
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                provider_request_id=response.id,
            ),
            finish_reason=response.stop_reason,
        )
