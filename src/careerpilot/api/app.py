from __future__ import annotations

from fastapi import FastAPI

from careerpilot.api.deps import ProfileApi
from careerpilot.api.errors import register_exception_handlers
from careerpilot.api.middleware import RequestIdMiddleware
from careerpilot.api.v1.jobs import router as jobs_router
from careerpilot.api.v1.profiles import router as profiles_router
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase


def create_app(
    *,
    search_jobs: SearchAndIngestJobsUseCase,
    profile_api: ProfileApi | None = None,
) -> FastAPI:
    """ASGI app. Job sources are injected by the caller; none are hard-coded."""
    app = FastAPI(title="CareerPilot AI", version="0.1.0", debug=False)
    app.state.search_jobs = search_jobs
    app.state.profile_api = profile_api
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(profiles_router, prefix="/api/v1")
    return app
