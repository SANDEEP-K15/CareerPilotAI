from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource
from tests.fakes.repositories import InMemoryJobRepository

from careerpilot.api.app import create_app
from careerpilot.api.schemas.jobs import JobResponse
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSourceError, JobSourceErrorCode, RawJob

_CANONICAL_JOB_FIELDS = set(JobResponse.model_fields)
_FORBIDDEN_API_FIELDS = {
    "extra",
    "metadata",
    "raw",
    "country",
    "adzuna",
    "app_id",
    "app_key",
    "redirect_url",
    "created",
}


def _raw(
    source: str,
    external_id: str,
    title: str,
    *,
    extra: dict[str, object] | None = None,
) -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title=title,
        company_name="Acme",
        source_url=f"https://example.com/jobs/{external_id}",
        application_url=f"https://apply.example.com/{external_id}",
        location="Remote",
        description="Build software.",
        extra=extra or {"vendor_only": "must-not-leak"},
    )


def _client(
    *sources: InMemoryJobSource,
    jobs: InMemoryJobRepository | None = None,
) -> tuple[TestClient, InMemoryJobRepository]:
    repository = jobs or InMemoryJobRepository()
    ingest = IngestRawJobUseCase(
        jobs=repository,
        clock=FrozenClock(),
        ids=FixedIdGenerator(*[uuid4() for _ in range(32)]),
    )
    use_case = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(sources)),
        ingest=ingest,
    )
    return TestClient(create_app(search_jobs=use_case)), repository


def test_successful_search_returns_canonical_jobs() -> None:
    source = InMemoryJobSource("example_board", (_raw("example_board", "ext-1", "ML Intern"),))
    client, jobs = _client(source)
    response = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "sources": ["example_board"]},
        headers={"X-Request-ID": "req-success"},
    )
    assert response.status_code == 200
    body = response.json()
    assert response.headers["X-Request-ID"] == "req-success"
    assert body["request_id"] == "req-success"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["title"] == "ML Intern"
    assert item["source"] == "example_board"
    assert item["external_id"] == "ext-1"
    assert item["company_name"] == "Acme"
    assert item["source_url"] == "https://example.com/jobs/ext-1"
    assert set(item) == _CANONICAL_JOB_FIELDS
    assert _FORBIDDEN_API_FIELDS.isdisjoint(item)
    assert jobs._by_id  # persisted


def test_empty_results() -> None:
    source = InMemoryJobSource("example_board", (_raw("example_board", "ext-1", "ML Intern"),))
    client, _jobs = _client(source)
    response = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["chemist"], "sources": ["example_board"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["errors"] == []
    assert body["sources"][0]["returned"] == 0


def test_invalid_request_missing_query() -> None:
    client, _jobs = _client()
    response = client.post("/api/v1/jobs/search", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_job_search_query"
    assert "traceback" not in body["error"]["message"].lower()
    assert "error" in body


def test_invalid_request_unknown_field() -> None:
    client, _jobs = _client()
    response = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "country": "gb"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_unknown_source() -> None:
    source = InMemoryJobSource("example_board", (_raw("example_board", "ext-1", "ML Intern"),))
    client, _jobs = _client(source)
    response = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "sources": ["missing_board"]},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "unknown_job_source"
    assert "missing_board" in body["error"]["message"]


def test_provider_failure_is_safe_and_does_not_500() -> None:
    broken = InMemoryJobSource(
        "broken",
        fail_with=RuntimeError("secret-token-must-not-leak"),
    )
    client, _jobs = _client(broken)
    response = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "sources": ["broken"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert len(body["errors"]) == 1
    assert body["errors"][0]["code"] == "unknown"
    assert body["errors"][0]["source"] == "broken"
    dumped = str(body)
    assert "secret-token-must-not-leak" not in dumped
    assert "traceback" not in dumped.lower()


def test_multiple_providers_partial_failure() -> None:
    healthy = InMemoryJobSource("healthy", (_raw("healthy", "1", "ML Intern"),))
    broken = InMemoryJobSource(
        "broken",
        fail_with=JobSourceError(
            "source unavailable",
            code=JobSourceErrorCode.UNAVAILABLE,
            source="broken",
            retryable=True,
        ),
    )
    client, _jobs = _client(healthy, broken)
    response = client.post("/api/v1/jobs/search", json={"keywords": ["intern"]})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["source"] == "healthy"
    assert body["errors"][0]["source"] == "broken"
    assert body["errors"][0]["retryable"] is True


def test_pagination() -> None:
    listings = tuple(
        _raw("example_board", str(index), f"ML Intern {index}") for index in range(3)
    )
    source = InMemoryJobSource("example_board", listings)
    client, _jobs = _client(source)
    first = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "page": 1, "page_size": 2, "sources": ["example_board"]},
    )
    second = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "page": 2, "page_size": 2, "sources": ["example_board"]},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["has_more"] is True
    assert first.json()["sources"][0]["has_more"] is True
    assert len(first.json()["items"]) == 2
    assert second.json()["has_more"] is False
    assert len(second.json()["items"]) == 1


def test_persistence_is_idempotent_across_searches() -> None:
    source = InMemoryJobSource("example_board", (_raw("example_board", "ext-9", "ML Intern"),))
    jobs = InMemoryJobRepository()
    client, _ = _client(source, jobs=jobs)
    first = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "sources": ["example_board"]},
    )
    second = client.post(
        "/api/v1/jobs/search",
        json={"keywords": ["intern"], "sources": ["example_board"]},
    )
    assert first.json()["items"][0]["id"] == second.json()["items"][0]["id"]
    assert len(jobs._by_id) == 1


def test_contract_has_no_provider_specific_fields() -> None:
    schema = JobResponse.model_json_schema()
    properties = schema.get("properties", {})
    assert _FORBIDDEN_API_FIELDS.isdisjoint(properties)
    dumped = str(schema).lower()
    assert "adzuna" not in dumped
    assert "gb" not in dumped
    assert "india" not in dumped
