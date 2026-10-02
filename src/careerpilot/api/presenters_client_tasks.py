from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from careerpilot.api.schemas.client_tasks import (
    ClientTaskErrorResponse,
    ClientTaskStepResponse,
    ClientTaskSubmitResponse,
)
from careerpilot.application.orchestration.results import OrchestrationResult, OrchestrationStatus


def orchestration_to_client_task_response(
    result: OrchestrationResult,
    *,
    request_id: str,
    correlation_id: str | None,
) -> ClientTaskSubmitResponse:
    steps = tuple(_step(item) for item in result.steps)
    error = None
    if result.status is OrchestrationStatus.FAILED:
        error = ClientTaskErrorResponse(
            code=result.error_code or "orchestration_failed",
            message=result.error_message or "Orchestration failed.",
        )
    output = _output(result.output.data if result.output is not None else None)
    return ClientTaskSubmitResponse(
        request_id=request_id,
        correlation_id=correlation_id,
        status=result.status.value,
        plan_id=result.plan_id,
        summary=result.summary,
        steps=steps,
        output=output,
        error=error,
    )


def _step(item: object) -> ClientTaskStepResponse:
    from careerpilot.application.orchestration.results import OrchestrationStepResult

    if not isinstance(item, OrchestrationStepResult):
        raise TypeError("expected OrchestrationStepResult")
    run = item.result
    return ClientTaskStepResponse(
        step_id=item.step_id,
        agent=item.agent.value,
        status=run.status.value,
        error_code=run.error_code,
        error_message=run.error_message,
    )


def _output(data: Mapping[str, object] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return dict(data)
