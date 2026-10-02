from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

from careerpilot.application.llm.configuration import LlmRuntimeConfiguration
from careerpilot.application.llm.errors import InvalidLlmInvocationError
from careerpilot.application.llm.registry import LlmProviderRegistry
from careerpilot.application.llm.results import LlmCompletionResult, LlmCompletionStatus
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.cost import CostManagerPort, LlmUsageEvent
from careerpilot.ports.llm import LlmMessage, LlmRequest, LlmResponse, normalize_llm_failure

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LlmInvocation:
    messages: tuple[LlmMessage, ...]
    provider: str | LlmProviderKey | None = None
    model: str | LlmModelId | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    correlation_id: str | None = None
    user_id: str | None = None
    task: str | None = None


class NoOpCostManager:
    async def record_llm_usage(self, event: LlmUsageEvent) -> None:
        del event


class InvokeLlmUseCase:
    """Resolve provider/model from configuration and run one LLM completion."""

    def __init__(
        self,
        *,
        registry: LlmProviderRegistry,
        configuration: LlmRuntimeConfiguration,
        cost_manager: CostManagerPort | None = None,
    ) -> None:
        self._registry = registry
        self._configuration = configuration
        self._cost_manager = cost_manager or NoOpCostManager()

    async def execute(self, invocation: LlmInvocation) -> LlmCompletionResult:
        messages = _normalize_messages(invocation.messages)
        provider_key = _resolve_provider(invocation.provider, self._configuration)
        model = _resolve_model(invocation.model, self._configuration)
        port = self._registry.get(provider_key)
        request = LlmRequest(
            model=model,
            messages=messages,
            temperature=invocation.temperature,
            max_output_tokens=invocation.max_output_tokens,
            metadata=dict(invocation.metadata),
        )
        try:
            response = await port.complete(request)
        except Exception as exc:
            error = normalize_llm_failure(provider_key.value, exc)
            return LlmCompletionResult(
                provider=provider_key.value,
                model=model,
                status=LlmCompletionStatus.FAILED,
                error_code=error.code.value,
                error_message=error.message,
            )
        await _record_usage(
            self._cost_manager,
            provider=provider_key,
            model=response.model,
            response=response,
            correlation_id=invocation.correlation_id,
            user_id=invocation.user_id,
            task=invocation.task,
        )
        return LlmCompletionResult(
            provider=provider_key.value,
            model=response.model,
            status=LlmCompletionStatus.SUCCESS,
            response=response,
        )


def _normalize_messages(messages: tuple[LlmMessage, ...]) -> tuple[LlmMessage, ...]:
    if not messages:
        raise InvalidLlmInvocationError("at least one message is required.")
    normalized: list[LlmMessage] = []
    for message in messages:
        content = " ".join(message.content.split())
        if not content:
            raise InvalidLlmInvocationError("message content must not be empty.")
        normalized.append(LlmMessage(role=message.role, content=content))
    return tuple(normalized)


def _resolve_provider(
    explicit: str | LlmProviderKey | None,
    configuration: LlmRuntimeConfiguration,
) -> LlmProviderKey:
    if explicit is not None:
        return (
            explicit
            if isinstance(explicit, LlmProviderKey)
            else LlmProviderKey.parse(explicit)
        )
    return configuration.require_default_provider()


def _resolve_model(
    explicit: str | LlmModelId | None,
    configuration: LlmRuntimeConfiguration,
) -> LlmModelId:
    if explicit is not None:
        return explicit if isinstance(explicit, LlmModelId) else LlmModelId.parse(explicit)
    return configuration.require_default_model()


async def _record_usage(
    cost_manager: CostManagerPort,
    *,
    provider: LlmProviderKey,
    model: LlmModelId,
    response: LlmResponse,
    correlation_id: str | None,
    user_id: str | None,
    task: str | None,
) -> None:
    event = LlmUsageEvent(
        provider=provider,
        model=model,
        usage=response.usage,
        correlation_id=correlation_id,
        user_id=user_id,
        task=task,
    )
    try:
        await cost_manager.record_llm_usage(event)
    except Exception:
        logger.exception("LLM usage recording failed for provider %s", provider.value)
