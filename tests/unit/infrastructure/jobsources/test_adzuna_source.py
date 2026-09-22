from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.infrastructure.jobsources.adzuna.settings import AdzunaSettings
from careerpilot.infrastructure.jobsources.adzuna.source import AdzunaJobSource
from careerpilot.ports.job_source import JobSearchQuery, JobSourceError, JobSourceErrorCode


def _settings() -> AdzunaSettings:
    return AdzunaSettings(
        app_id=SecretStr("test-app-id"),
        app_key=SecretStr("test-app-key"),
        country="gb",
        timeout_seconds=2,
    )


def _job(job_id: str = "1", title: str = "ML Intern") -> dict[str, object]:
    return {
        "id": job_id,
        "title": title,
        "company": {"display_name": "Acme"},
        "redirect_url": f"https://www.adzuna.co.uk/jobs/land/ad/{job_id}",
        "created": "2026-01-15T12:00:00Z",
        "location": {"display_name": "London, UK"},
        "description": "An internship.",
    }


def _source(
    transport: httpx.MockTransport | None = None,
    settings: AdzunaSettings | None = None,
) -> AdzunaJobSource:
    client = httpx.AsyncClient(transport=transport) if transport is not None else None
    return AdzunaJobSource(settings or _settings(), client=client)


def _transport(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


async def test_successful_search_maps_raw_jobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/jobs/gb/search/1")
        assert request.url.params["what"] == "ml intern"
        assert request.url.params["where"] == "London"
        assert request.url.params["results_per_page"] == "20"
        assert request.url.params["app_id"] == "test-app-id"
        return httpx.Response(200, json={"count": 1, "results": [_job()]})

    page = await _source(_transport(handler)).search(
        JobSearchQuery(keywords=("ml intern",), location="London")
    )
    assert len(page.items) == 1
    assert page.items[0].source.value == "adzuna"
    assert page.items[0].title == "ML Intern"
    assert page.has_more is False


async def test_multiple_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"count": 2, "results": [_job("1"), _job("2", title="Data Intern")]},
        )

    page = await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert [item.external_id for item in page.items] == ["1", "2"]


async def test_empty_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"count": 0, "results": []})

    page = await _source(_transport(handler)).search(JobSearchQuery(keywords=(" intern ",)))
    assert page.items == ()
    assert page.has_more is False


async def test_pagination_path_and_has_more() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/jobs/gb/search/2")
        assert request.url.params["results_per_page"] == "2"
        return httpx.Response(200, json={"count": 5, "results": [_job("3"), _job("4")]})

    page = await _source(_transport(handler)).search(
        JobSearchQuery(keywords=("intern",), page=2, page_size=2)
    )
    assert page.page == 2
    assert page.has_more is True


async def test_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.MALFORMED_RESPONSE


async def test_missing_results_array_is_malformed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"count": 1})

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.MALFORMED_RESPONSE


async def test_authentication_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"exception": "unauthorized"})

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.UNAUTHORIZED
    assert exc.value.retryable is False


async def test_rate_limiting() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"exception": "rate_limited"})

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.RATE_LIMITED
    assert exc.value.retryable is True


async def test_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("late")

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.TIMEOUT
    assert exc.value.retryable is True


async def test_server_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"exception": "unavailable"})

    with pytest.raises(JobSourceError) as exc:
        await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.UNAVAILABLE


async def test_invalid_listing_fields_are_skipped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"results": [_job(), {"title": "No id"}, "ignore-me"]},
        )

    page = await _source(_transport(handler)).search(JobSearchQuery(keywords=("intern",)))
    assert len(page.items) == 1


async def test_missing_credentials_does_not_call_http() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"results": []})

    settings = AdzunaSettings(app_id=SecretStr(""), app_key=SecretStr(""))
    source = _source(_transport(handler), settings=settings)
    with pytest.raises(JobSourceError) as exc:
        await source.search(JobSearchQuery(keywords=("intern",)))
    assert exc.value.code is JobSourceErrorCode.UNAVAILABLE
    assert called is False


async def test_registry_accepts_adzuna_adapter_without_application_importing_it() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [_job()]})

    registry = JobSourceRegistry()
    registry.register(_source(_transport(handler)))
    port = registry.get("adzuna")
    page = await port.search(JobSearchQuery(keywords=("intern",)))
    assert page.items[0].source.value == "adzuna"


def test_error_messages_do_not_include_secrets() -> None:
    error = JobSourceError(
        "Adzuna rejected the request credentials.",
        code=JobSourceErrorCode.UNAUTHORIZED,
        source="adzuna",
    )
    dumped = json.dumps({"message": error.message, "code": error.code})
    assert "test-app-key" not in dumped
    assert "app_key" not in dumped
