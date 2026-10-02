from __future__ import annotations

from careerpilot.api.schemas.application_prep import (
    ApplicationPrepInterviewQuestionResponse,
    ApplicationPrepPackageResponse,
    ApplicationPrepTalkingPointResponse,
)
from careerpilot.api.schemas.approval_requests import (
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
)
from careerpilot.api.schemas.jobs import (
    JobResponse,
    JobSearchResponse,
    SourceErrorResponse,
    SourcePageResponse,
)
from careerpilot.api.schemas.matches import JobMatchResponse, MatchReportResponse
from careerpilot.api.schemas.profiles import CareerProfileResponse, ResumeResponse
from careerpilot.api.schemas.resume_tailoring import (
    ResumeTailoringChangeResponse,
    ResumeTailoringResponse,
)
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestResult
from careerpilot.domain.entities.application_prep import ApplicationPrepPackage
from careerpilot.domain.entities.approval_request import ApprovalRequest
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.job_match import MatchReport
from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.entities.resume_tailoring import ResumeTailoringResult


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


def resume_tailoring_to_response(
    result: ResumeTailoringResult,
    *,
    request_id: str,
) -> ResumeTailoringResponse:
    return ResumeTailoringResponse(
        user_id=result.user_id,
        job_id=result.job_id,
        source_resume_id=result.source_resume_id,
        source_resume_version=result.source_resume_version,
        tailored_content=result.tailored_content,
        changes=tuple(
            ResumeTailoringChangeResponse(section=item.section, description=item.description)
            for item in result.changes
        ),
        llm_provider=result.llm_provider,
        llm_model=result.llm_model,
        request_id=request_id,
    )


def application_prep_to_response(
    package: ApplicationPrepPackage,
    *,
    request_id: str,
) -> ApplicationPrepPackageResponse:
    return ApplicationPrepPackageResponse(
        user_id=package.user_id,
        job_id=package.job_id,
        source_resume_id=package.source_resume_id,
        source_resume_version=package.source_resume_version,
        guidance=package.guidance,
        talking_points=tuple(
            ApplicationPrepTalkingPointResponse(section=item.section, point=item.point)
            for item in package.talking_points
        ),
        interview_questions=tuple(
            ApplicationPrepInterviewQuestionResponse(
                question=item.question,
                focus=item.focus,
            )
            for item in package.interview_questions
        ),
        llm_provider=package.llm_provider,
        llm_model=package.llm_model,
        request_id=request_id,
    )


def approval_request_to_response(
    item: ApprovalRequest,
    *,
    request_id: str,
) -> ApprovalRequestResponse:
    return ApprovalRequestResponse(
        id=item.id,
        user_id=item.user_id,
        job_id=item.job_id,
        action=item.action.value,
        status=item.status.value,
        reason=item.reason,
        decision_note=item.decision_note,
        expires_at=item.expires_at,
        decided_at=item.decided_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        request_id=request_id,
    )


def approval_request_list_to_response(
    items: tuple[ApprovalRequest, ...],
    *,
    request_id: str,
) -> ApprovalRequestListResponse:
    return ApprovalRequestListResponse(
        items=tuple(approval_request_to_response(item, request_id=request_id) for item in items),
        request_id=request_id,
    )


def match_report_to_response(report: MatchReport, *, request_id: str) -> MatchReportResponse:
    return MatchReportResponse(
        user_id=report.user_id,
        profile_id=report.profile_id,
        threshold=report.threshold,
        considered=report.considered,
        rejected=report.rejected,
        items=tuple(
            JobMatchResponse(
                job_id=item.job_id,
                score=item.score,
                matched_skills=item.matched_skills,
                missing_skills=item.missing_skills,
                reasons=item.reasons,
                concerns=item.concerns,
            )
            for item in report.matches
        ),
        request_id=request_id,
    )
