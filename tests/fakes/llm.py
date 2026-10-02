from __future__ import annotations

from decimal import Decimal

from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.llm import (
    LlmError,
    LlmErrorCode,
    LlmReportedCost,
    LlmRequest,
    LlmResponse,
    LlmUsage,
)


class FakeLlmProvider:
    """Deterministic LlmPort for tests. Never performs HTTP."""

    def __init__(
        self,
        name: str = "fake",
        *,
        response_text: str = "ok",
        fail_with: BaseException | None = None,
        include_reported_cost: bool = False,
    ) -> None:
        self._key = LlmProviderKey.parse(name)
        self._response_text = response_text
        self._fail_with = fail_with
        self._include_reported_cost = include_reported_cost
        self.last_request: LlmRequest | None = None

    @property
    def provider_key(self) -> LlmProviderKey:
        return self._key

    async def complete(self, request: LlmRequest) -> LlmResponse:
        self.last_request = request
        if self._fail_with is not None:
            if isinstance(self._fail_with, LlmError):
                raise self._fail_with
            raise self._fail_with
        prompt_tokens = sum(len(message.content.split()) for message in request.messages)
        completion_tokens = len(self._response_text.split())
        cost = None
        if self._include_reported_cost:
            cost = LlmReportedCost(amount=Decimal("0.001"), currency="USD")
        usage = LlmUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider_request_id="fake-req-1",
            reported_cost=cost,
        )
        return LlmResponse(
            content=self._response_text,
            model=request.model,
            usage=usage,
            finish_reason="stop",
        )


class CodedLlmFailureProvider(FakeLlmProvider):
    def __init__(self, name: str = "fake") -> None:
        super().__init__(
            name,
            fail_with=LlmError(
                "request rejected",
                code=LlmErrorCode.INVALID_REQUEST,
                provider=name,
            ),
        )
