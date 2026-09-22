from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request

from careerpilot.api.deps import ProfileApi
from careerpilot.api.presenters import profile_to_response, resume_to_response
from careerpilot.api.schemas.profiles import (
    CareerProfileRequest,
    CareerProfileResponse,
    ResumeCreateRequest,
    ResumeListResponse,
    ResumeResponse,
)
from careerpilot.application.errors import ApplicationError
from careerpilot.application.use_cases.career_profile import SaveCareerProfileCommand
from careerpilot.application.use_cases.resume import AddResumeVersionCommand

router = APIRouter()


def _profile_api(request: Request) -> ProfileApi:
    api = getattr(request.app.state, "profile_api", None)
    if not isinstance(api, ProfileApi):
        raise ApplicationError("Career profile API is not configured.", code="not_configured")
    return api


@router.put("/users/{user_id}/profile", response_model=CareerProfileResponse)
async def save_profile(
    user_id: UUID, payload: CareerProfileRequest, request: Request
) -> CareerProfileResponse:
    profile = await _profile_api(request).save_profile.execute(
        SaveCareerProfileCommand(
            user_id=user_id,
            headline=payload.headline,
            summary=payload.summary,
            skills=payload.skills,
            target_titles=payload.target_titles,
            locations=payload.locations,
            remote_policy=payload.remote_policy,
            employment_type=payload.employment_type,
            years_experience=payload.years_experience,
        )
    )
    return profile_to_response(profile)


@router.get("/users/{user_id}/profile", response_model=CareerProfileResponse)
async def get_profile(user_id: UUID, request: Request) -> CareerProfileResponse:
    profile = await _profile_api(request).get_profile.execute(user_id)
    return profile_to_response(profile)


@router.post("/users/{user_id}/resumes", response_model=ResumeResponse)
async def add_resume(
    user_id: UUID, payload: ResumeCreateRequest, request: Request
) -> ResumeResponse:
    resume = await _profile_api(request).add_resume.execute(
        AddResumeVersionCommand(user_id=user_id, content=payload.content, label=payload.label)
    )
    return resume_to_response(resume)


@router.get("/users/{user_id}/resumes", response_model=ResumeListResponse)
async def list_resumes(user_id: UUID, request: Request) -> ResumeListResponse:
    items = await _profile_api(request).list_resumes.execute(user_id)
    return ResumeListResponse(items=tuple(resume_to_response(item) for item in items))


@router.get("/users/{user_id}/resumes/active", response_model=ResumeResponse)
async def get_active_resume(user_id: UUID, request: Request) -> ResumeResponse:
    resume = await _profile_api(request).get_active_resume.execute(user_id)
    return resume_to_response(resume)


@router.get("/users/{user_id}/resumes/{version}", response_model=ResumeResponse)
async def get_resume_version(
    user_id: UUID, version: int, request: Request
) -> ResumeResponse:
    resume = await _profile_api(request).get_resume_version.execute(user_id, version)
    return resume_to_response(resume)
