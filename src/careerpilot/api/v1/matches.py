from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters import match_report_to_response
from careerpilot.api.schemas.matches import MatchReportResponse
from careerpilot.application.errors import ApplicationError
from careerpilot.application.use_cases.match_jobs import MatchJobsCommand, MatchJobsUseCase
from careerpilot.domain.matching import DEFAULT_LIMIT, DEFAULT_THRESHOLD, MAX_LIMIT

router = APIRouter()


def _match_jobs(request: Request) -> MatchJobsUseCase:
    use_case = getattr(request.app.state, "match_jobs", None)
    if not isinstance(use_case, MatchJobsUseCase):
        raise ApplicationError("Job matching API is not configured.", code="not_configured")
    return use_case


@router.get("/users/{user_id}/matches", response_model=MatchReportResponse)
async def match_jobs(
    user_id: UUID,
    request: Request,
    threshold: int = Query(default=DEFAULT_THRESHOLD, ge=0, le=100),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> MatchReportResponse:
    result = await _match_jobs(request).execute(
        MatchJobsCommand(user_id=user_id, threshold=threshold, limit=limit)
    )
    return match_report_to_response(result, request_id=request_id_of(request))
