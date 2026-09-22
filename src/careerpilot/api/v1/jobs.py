from __future__ import annotations

from fastapi import APIRouter, Request

from careerpilot.api.errors import request_id_of
from careerpilot.api.presenters import search_result_to_response
from careerpilot.api.schemas.jobs import JobSearchRequest, JobSearchResponse
from careerpilot.application.use_cases.search_and_ingest_jobs import (
    SearchAndIngestJobsUseCase,
    SearchJobsCommand,
)

router = APIRouter()


@router.post("/jobs/search", response_model=JobSearchResponse)
async def search_jobs(payload: JobSearchRequest, request: Request) -> JobSearchResponse:
    use_case: SearchAndIngestJobsUseCase = request.app.state.search_jobs
    result = await use_case.execute(
        SearchJobsCommand(
            keywords=payload.keywords,
            location=payload.location,
            remote_only=payload.remote_only,
            page=payload.page,
            page_size=payload.page_size,
            sources=payload.sources,
        )
    )
    return search_result_to_response(result, request_id=request_id_of(request))
