from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters import application_prep_to_response
from careerpilot.api.schemas.application_prep import (
    ApplicationPrepPackageResponse,
    PrepareApplicationRequest,
)
from careerpilot.application.application_preparation import (
    PrepareApplicationCommand,
    PrepareApplicationUseCase,
)
from careerpilot.application.errors import ApplicationError

router = APIRouter()


def _prepare_application(request: Request) -> PrepareApplicationUseCase:
    use_case = getattr(request.app.state, "prepare_application", None)
    if not isinstance(use_case, PrepareApplicationUseCase):
        raise ApplicationError(
            "Application preparation API is not configured.",
            code="not_configured",
        )
    return use_case


@router.post(
    "/users/{user_id}/applications/prepare",
    response_model=ApplicationPrepPackageResponse,
)
async def prepare_application(
    user_id: UUID,
    payload: PrepareApplicationRequest,
    request: Request,
) -> ApplicationPrepPackageResponse:
    request_id = request_id_of(request)
    package = await _prepare_application(request).execute(
        PrepareApplicationCommand(
            user_id=user_id,
            job_id=payload.job_id,
            correlation_id=request_id,
        )
    )
    return application_prep_to_response(package, request_id=request_id)
