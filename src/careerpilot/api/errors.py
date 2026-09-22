from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from careerpilot.application.errors import ApplicationError
from careerpilot.application.job_sources.errors import UnknownJobSourceError
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
    @app.exception_handler(UnknownJobSourceError)
    async def unknown_source(_request: Request, exc: UnknownJobSourceError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
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
