from __future__ import annotations

from careerpilot.api.schemas.jobs import (
    JobResponse,
    JobSearchResponse,
    SourceErrorResponse,
    SourcePageResponse,
)
from careerpilot.api.schemas.profiles import CareerProfileResponse, ResumeResponse
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestResult
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume


def job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        source=job.source.value,
        external_id=job.external_id,
        title=job.title,
        company_name=job.company_name,
        source_url=job.source_url,
        application_url=job.application_url,
        location=job.location,
        remote_policy=job.remote_policy.value,
        employment_type=job.employment_type.value,
        description=job.description,
        posted_at=job.posted_at,
        discovered_at=job.discovered_at,
        content_hash=job.content_hash,
        status=job.status.value,
    )


def search_result_to_response(
    result: SearchAndIngestResult, *, request_id: str
) -> JobSearchResponse:
    return JobSearchResponse(
        items=tuple(job_to_response(job) for job in result.jobs),
        page=result.page,
        page_size=result.page_size,
        has_more=result.has_more,
        sources=tuple(
            SourcePageResponse(
                source=item.source.value,
                page=item.page,
                page_size=item.page_size,
                returned=item.returned,
                has_more=item.has_more,
            )
            for item in result.sources
        ),
        errors=tuple(
            SourceErrorResponse(
                source=failure.source.value,
                code=failure.error.code.value,
                message=failure.error.message,
                retryable=failure.error.retryable,
            )
            for failure in result.failures
        ),
        request_id=request_id,
    )


def profile_to_response(profile: CareerProfile) -> CareerProfileResponse:
    return CareerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        headline=profile.headline,
        summary=profile.summary,
        skills=profile.skills,
        target_titles=profile.target_titles,
        locations=profile.locations,
        remote_policy=profile.remote_policy.value,
        employment_type=profile.employment_type.value,
        years_experience=profile.years_experience,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def resume_to_response(resume: Resume) -> ResumeResponse:
    return ResumeResponse(
        id=resume.id,
        user_id=resume.user_id,
        version=resume.version,
        label=resume.label,
        content=resume.content,
        content_type=resume.content_type.value,
        is_active=resume.is_active,
        created_at=resume.created_at,
    )
