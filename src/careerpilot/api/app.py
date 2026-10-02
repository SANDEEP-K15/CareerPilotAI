from __future__ import annotations

from fastapi import FastAPI

from careerpilot.api.deps import ProfileApi
from careerpilot.api.errors import register_exception_handlers
from careerpilot.api.middleware import RequestIdMiddleware
from careerpilot.api.v1.client_tasks import router as client_tasks_router
from careerpilot.api.v1.jobs import router as jobs_router
from careerpilot.api.v1.matches import router as matches_router
from careerpilot.api.v1.profiles import router as profiles_router
from careerpilot.api.v1.resume_tailoring import router as resume_tailoring_router
from careerpilot.application.client_tasks import SubmitClientTaskUseCase
from careerpilot.application.resume_tailoring import TailorResumeUseCase
from careerpilot.application.use_cases.match_jobs import MatchJobsUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.config.settings import ClientApiSettings


def create_app(
    *,
    search_jobs: SearchAndIngestJobsUseCase,
    profile_api: ProfileApi | None = None,
    match_jobs: MatchJobsUseCase | None = None,
    submit_client_task: SubmitClientTaskUseCase | None = None,
    client_api_settings: ClientApiSettings | None = None,
    tailor_resume: TailorResumeUseCase | None = None,
) -> FastAPI:
    """ASGI app. Job sources are injected by the caller; none are hard-coded."""
    app = FastAPI(title="CareerPilot AI", version="0.1.0", debug=False)
    app.state.search_jobs = search_jobs
    app.state.profile_api = profile_api
    app.state.match_jobs = match_jobs
    app.state.submit_client_task = submit_client_task
    app.state.client_api_settings = client_api_settings
    app.state.tailor_resume = tailor_resume
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(profiles_router, prefix="/api/v1")
    app.include_router(matches_router, prefix="/api/v1")
    app.include_router(client_tasks_router, prefix="/api/v1")
    app.include_router(resume_tailoring_router, prefix="/api/v1")
    return app
