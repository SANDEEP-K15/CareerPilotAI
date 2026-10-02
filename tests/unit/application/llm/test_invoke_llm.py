from __future__ import annotations

from decimal import Decimal

import pytest
from tests.fakes.llm import CodedLlmFailureProvider, FakeLlmProvider

from careerpilot.application.llm import (
    InvalidLlmInvocationError,
    InvokeLlmUseCase,
    LlmCompletionStatus,
    LlmConfigurationError,
    LlmInvocation,
    LlmProviderRegistry,
    LlmRuntimeConfiguration,
)
from careerpilot.application.llm.errors import UnknownLlmProviderError
from careerpilot.config.settings import LlmSettings
from careerpilot.domain.value_objects.llm_model_id import LlmModelId
from careerpilot.domain.value_objects.llm_provider_key import LlmProviderKey
from careerpilot.ports.cost import CostManagerPort, LlmUsageEvent
from careerpilot.ports.llm import LlmMessage, LlmRole, normalize_llm_failure


async def test_invoke_uses_configured_defaults() -> None:
    provider = FakeLlmProvider("lab", response_text="done")
    registry = LlmProviderRegistry((provider,))
    configuration = LlmRuntimeConfiguration.from_settings(
        LlmSettings(provider="lab", default_model="demo-model")
    )
    use_case = InvokeLlmUseCase(registry=registry, configuration=configuration)
    result = await use_case.execute(
        LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="hello"),))
    )
    assert result.succeeded
    assert result.response is not None
    assert result.response.content == "done"
    assert provider.last_request is not None
    assert provider.last_request.model.value == "demo-model"


async def test_invoke_honors_explicit_provider_and_model() -> None:
    provider = FakeLlmProvider("custom")
    use_case = InvokeLlmUseCase(
        registry=LlmProviderRegistry((provider,)),
        configuration=LlmRuntimeConfiguration(),
    )
    result = await use_case.execute(
        LlmInvocation(
            provider="custom",
            model="other-model",
            messages=(LlmMessage(role=LlmRole.USER, content="ping"),),
        )
    )
    assert result.succeeded
    assert result.model.value == "other-model"


async def test_missing_configuration_raises() -> None:
    use_case = InvokeLlmUseCase(
        registry=LlmProviderRegistry((FakeLlmProvider("lab"),)),
        configuration=LlmRuntimeConfiguration(),
    )
    with pytest.raises(LlmConfigurationError):
        await use_case.execute(
            LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="x"),))
        )


async def test_unknown_provider_raises() -> None:
    use_case = InvokeLlmUseCase(
        registry=LlmProviderRegistry(),
        configuration=LlmRuntimeConfiguration(
            default_provider=LlmProviderKey.parse("lab"),
            default_model=LlmModelId.parse("demo-model"),
        ),
    )
    with pytest.raises(UnknownLlmProviderError):
        await use_case.execute(
            LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="x"),))
        )


async def test_invalid_messages_are_rejected() -> None:
    use_case = InvokeLlmUseCase(
        registry=LlmProviderRegistry((FakeLlmProvider("lab"),)),
        configuration=LlmRuntimeConfiguration(
            default_provider=LlmProviderKey.parse("lab"),
            default_model=LlmModelId.parse("demo-model"),
        ),
    )
    with pytest.raises(InvalidLlmInvocationError):
        await use_case.execute(LlmInvocation(messages=()))


async def test_llm_failure_returns_structured_result() -> None:
    registry = LlmProviderRegistry((CodedLlmFailureProvider("lab"),))
    configuration = LlmRuntimeConfiguration(
        default_provider=LlmProviderKey.parse("lab"),
        default_model=LlmModelId.parse("demo-model"),
    )
    result = await InvokeLlmUseCase(registry=registry, configuration=configuration).execute(
        LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="run"),))
    )
    assert result.status is LlmCompletionStatus.FAILED
    assert result.error_code == "invalid_request"
    assert result.response is None


async def test_runtime_exception_is_normalized_without_leaking_details() -> None:
    registry = LlmProviderRegistry(
        (FakeLlmProvider("lab", fail_with=RuntimeError("secret-token-must-not-leak")),)
    )
    configuration = LlmRuntimeConfiguration(
        default_provider=LlmProviderKey.parse("lab"),
        default_model=LlmModelId.parse("demo-model"),
    )
    result = await InvokeLlmUseCase(registry=registry, configuration=configuration).execute(
        LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="run"),))
    )
    assert result.status is LlmCompletionStatus.FAILED
    assert result.error_code == "unknown"
    assert "secret-token" not in (result.error_message or "")


def test_normalize_llm_failure_maps_timeout() -> None:
    error = normalize_llm_failure("lab", TimeoutError())
    assert error.code.value == "timeout"
    assert error.retryable is True


class RecordingCostManager(CostManagerPort):
    def __init__(self) -> None:
        self.events: list[LlmUsageEvent] = []

    async def record_llm_usage(self, event: LlmUsageEvent) -> None:
        self.events.append(event)


async def test_invoke_records_usage_without_failing_on_cost_errors() -> None:
    provider = FakeLlmProvider("lab", include_reported_cost=True)

    class FailingCostManager(CostManagerPort):
        async def record_llm_usage(self, event: LlmUsageEvent) -> None:
            del event
            raise RuntimeError("ledger unavailable")

    result = await InvokeLlmUseCase(
        registry=LlmProviderRegistry((provider,)),
        configuration=LlmRuntimeConfiguration(
            default_provider=LlmProviderKey.parse("lab"),
            default_model=LlmModelId.parse("demo-model"),
        ),
        cost_manager=FailingCostManager(),
    ).execute(LlmInvocation(messages=(LlmMessage(role=LlmRole.USER, content="one"),)))
    assert result.succeeded


async def test_invoke_records_usage_event() -> None:
    cost_manager = RecordingCostManager()
    provider = FakeLlmProvider("lab", include_reported_cost=True)
    await InvokeLlmUseCase(
        registry=LlmProviderRegistry((provider,)),
        configuration=LlmRuntimeConfiguration(
            default_provider=LlmProviderKey.parse("lab"),
            default_model=LlmModelId.parse("demo-model"),
        ),
        cost_manager=cost_manager,
    ).execute(
        LlmInvocation(
            messages=(LlmMessage(role=LlmRole.USER, content="one two"),),
            correlation_id="corr-1",
            user_id="user-1",
            task="test-task",
        )
    )
    assert len(cost_manager.events) == 1
    event = cost_manager.events[0]
    assert event.correlation_id == "corr-1"
    assert event.usage.reported_cost is not None
    assert event.usage.reported_cost.amount == Decimal("0.001")
