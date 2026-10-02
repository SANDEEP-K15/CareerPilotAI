from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from careerpilot.api.auth import require_client_api_token
from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters_client_tasks import orchestration_to_client_task_response
from careerpilot.api.schemas.client_tasks import ClientTaskSubmitRequest, ClientTaskSubmitResponse
from careerpilot.application.client_tasks import (
    ClientTaskServiceUnavailableError,
    SubmitClientTaskCommand,
    SubmitClientTaskUseCase,
)

router = APIRouter()


def _submit_client_task(request: Request) -> SubmitClientTaskUseCase:
    use_case = getattr(request.app.state, "submit_client_task", None)
    if not isinstance(use_case, SubmitClientTaskUseCase):
        raise ClientTaskServiceUnavailableError()
    return use_case


@router.post(
    "/client/tasks",
    response_model=ClientTaskSubmitResponse,
    dependencies=[Depends(require_client_api_token)],
)
async def submit_client_task(
    payload: ClientTaskSubmitRequest,
    request: Request,
    use_case: Annotated[SubmitClientTaskUseCase, Depends(_submit_client_task)],
) -> ClientTaskSubmitResponse:
    request_id = request_id_of(request)
    correlation_id = payload.correlation_id or request_id
    result = await use_case.execute(
        SubmitClientTaskCommand(
            user_id=payload.user_id,
            intent=payload.intent,
            parameters=dict(payload.parameters),
            correlation_id=correlation_id,
            request_id=request_id,
        )
    )
    return orchestration_to_client_task_response(
        result,
        request_id=request_id,
        correlation_id=correlation_id,
    )
