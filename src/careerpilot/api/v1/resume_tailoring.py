from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters import resume_tailoring_to_response
from careerpilot.api.schemas.resume_tailoring import ResumeTailoringResponse, TailorResumeRequest
from careerpilot.application.errors import ApplicationError
from careerpilot.application.resume_tailoring import TailorResumeCommand, TailorResumeUseCase

router = APIRouter()


def _tailor_resume(request: Request) -> TailorResumeUseCase:
    use_case = getattr(request.app.state, "tailor_resume", None)
    if not isinstance(use_case, TailorResumeUseCase):
        raise ApplicationError("Resume tailoring API is not configured.", code="not_configured")
    return use_case


@router.post(
    "/users/{user_id}/resumes/tailor",
    response_model=ResumeTailoringResponse,
)
async def tailor_resume(
    user_id: UUID,
    payload: TailorResumeRequest,
    request: Request,
) -> ResumeTailoringResponse:
    request_id = request_id_of(request)
    result = await _tailor_resume(request).execute(
        TailorResumeCommand(
            user_id=user_id,
            job_id=payload.job_id,
            correlation_id=request_id,
        )
    )
    return resume_tailoring_to_response(result, request_id=request_id)
