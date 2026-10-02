from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from careerpilot.api.auth import ClientAuthenticationError
from careerpilot.application.application_preparation import ApplicationPreparationFailedError
from careerpilot.application.client_tasks.errors import (
    ClientTaskServiceUnavailableError,
    ClientTaskTimeoutError,
)
from careerpilot.application.errors import (
    ApplicationError,
    ApprovalRequestNotFoundError,
    CareerProfileAlreadyExistsError,
    CareerProfileNotFoundError,
    DuplicatePendingApprovalError,
    InvalidApprovalTransitionError,
    JobNotFoundError,
    ResumeNotFoundError,
    UserNotFoundError,
)
from careerpilot.application.job_sources.errors import UnknownJobSourceError
from careerpilot.application.resume_tailoring import ResumeTailoringFailedError
from careerpilot.application.use_cases.match_jobs import InvalidMatchQueryError
from careerpilot.domain.errors import DomainError
from careerpilot.ports.job_source import InvalidJobSearchQueryError


def request_id_of(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if isinstance(value, str) and value:
        return value
    header = request.headers.get("x-request-id")
    return header or "unknown"


def error_body(request: Request, *, code: str, message: str) -> dict[str, object]:
    return {
        "error": {"code": code, "message": message},
        "request_id": request_id_of(request),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ClientAuthenticationError)
    async def client_unauthorized(
        _request: Request, exc: ClientAuthenticationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ClientTaskTimeoutError)
    async def client_task_timeout(
        _request: Request, exc: ClientTaskTimeoutError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ClientTaskServiceUnavailableError)
    async def client_task_unavailable(
        _request: Request, exc: ClientTaskServiceUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(UnknownJobSourceError)
    async def unknown_source(_request: Request, exc: UnknownJobSourceError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found(_request: Request, exc: UserNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(CareerProfileNotFoundError)
    async def profile_not_found(
        _request: Request, exc: CareerProfileNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ResumeNotFoundError)
    async def resume_not_found(_request: Request, exc: ResumeNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(JobNotFoundError)
    async def job_not_found(_request: Request, exc: JobNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ApprovalRequestNotFoundError)
    async def approval_request_not_found(
        _request: Request, exc: ApprovalRequestNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(DuplicatePendingApprovalError)
    async def duplicate_pending_approval(
        _request: Request, exc: DuplicatePendingApprovalError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(InvalidApprovalTransitionError)
    async def invalid_approval_transition(
        _request: Request, exc: InvalidApprovalTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ResumeTailoringFailedError)
    async def resume_tailoring_failed(
        _request: Request, exc: ResumeTailoringFailedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ApplicationPreparationFailedError)
    async def application_preparation_failed(
        _request: Request, exc: ApplicationPreparationFailedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(CareerProfileAlreadyExistsError)
    async def profile_exists(
        _request: Request, exc: CareerProfileAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(InvalidJobSearchQueryError)
    async def invalid_query(
        _request: Request, exc: InvalidJobSearchQueryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(InvalidMatchQueryError)
    async def invalid_match(
        _request: Request, exc: InvalidMatchQueryError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(ApplicationError)
    async def application_error(_request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(_request, code=exc.code, message=exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del exc
        return JSONResponse(
            status_code=422,
            content=error_body(
                _request,
                code="invalid_request",
                message="Request body failed validation.",
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected(_request: Request, exc: Exception) -> JSONResponse:
        del exc
        return JSONResponse(
            status_code=500,
            content=error_body(
                _request,
                code="internal_error",
                message="An unexpected error occurred.",
            ),
        )
