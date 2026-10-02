from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr
from tests.fakes.agent import StubAgent
from tests.fakes.clock import FrozenClock
from tests.fakes.repositories import InMemoryJobRepository

from careerpilot.api.app import create_app
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.client_tasks import SubmitClientTaskUseCase
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.orchestration import build_executive
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.config.settings import ClientApiSettings
from careerpilot.infrastructure.http.careerpilot_api_client import (
    CareerPilotApiClient,
    CareerPilotApiError,
)
from careerpilot.ports.task_planner import UserTaskRequest


class _Ids:
    def new_id(self) -> UUID:
        return uuid4()


def _search_use_case() -> SearchAndIngestJobsUseCase:
    jobs = InMemoryJobRepository()
    return SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry()),
        ingest=IngestRawJobUseCase(
            jobs=jobs,
            clock=FrozenClock(),
            ids=_Ids(),
        ),
    )


def _client_task_app(
    *,
    timeout_seconds: float = 5.0,
    token: str = "test-client-token",
) -> TestClient:
    registry = AgentRegistry((StubAgent("helper"),))
    use_case = SubmitClientTaskUseCase(
        executive=build_executive(registry=registry),
        timeout_seconds=timeout_seconds,
    )
    settings = ClientApiSettings(api_token=SecretStr(token))
    app = create_app(
        search_jobs=_search_use_case(),
        submit_client_task=use_case,
        client_api_settings=settings,
    )
    return TestClient(app)


def test_client_task_requires_bearer_token() -> None:
    client = _client_task_app()
    response = client.post(
        "/api/v1/client/tasks",
        json={"user_id": str(uuid4()), "intent": "helper", "parameters": {}},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert response.headers["X-Request-ID"]


def test_client_task_submits_to_executive() -> None:
    user_id = uuid4()
    client = _client_task_app()
    response = client.post(
        "/api/v1/client/tasks",
        json={
            "user_id": str(user_id),
            "intent": "helper",
            "parameters": {"value": 3},
            "correlation_id": "corr-hermes-1",
        },
        headers={"Authorization": "Bearer test-client-token", "X-Request-ID": "req-1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "req-1"
    assert body["correlation_id"] == "corr-hermes-1"
    assert body["status"] == "success"
    assert body["steps"][0]["agent"] == "helper"
    assert body["output"]["value"] == 3


def test_client_task_returns_structured_orchestration_failure() -> None:
    from tests.fakes.agent import CodedFailureAgent

    registry = AgentRegistry((CodedFailureAgent("helper"),))
    use_case = SubmitClientTaskUseCase(executive=build_executive(registry=registry))
    app = create_app(
        search_jobs=_search_use_case(),
        submit_client_task=use_case,
        client_api_settings=ClientApiSettings(api_token=SecretStr("test-client-token")),
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/client/tasks",
        json={"user_id": str(uuid4()), "intent": "helper"},
        headers={"Authorization": "Bearer test-client-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "task_rejected"


def test_client_task_unavailable_when_use_case_missing() -> None:
    app = create_app(
        search_jobs=_search_use_case(),
        client_api_settings=ClientApiSettings(api_token=SecretStr("test-client-token")),
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/client/tasks",
        json={"user_id": str(uuid4()), "intent": "helper"},
        headers={"Authorization": "Bearer test-client-token"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "client_task_unavailable"


def test_client_task_timeout_returns_504() -> None:
    class SlowExecutive:
        async def run(self, request: UserTaskRequest):  # type: ignore[no-untyped-def]
            del request
            await asyncio.sleep(0.05)
            return None

    use_case = SubmitClientTaskUseCase(executive=SlowExecutive(), timeout_seconds=0.01)
    app = create_app(
        search_jobs=_search_use_case(),
        submit_client_task=use_case,
        client_api_settings=ClientApiSettings(api_token=SecretStr("test-client-token")),
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/client/tasks",
        json={"user_id": str(uuid4()), "intent": "helper"},
        headers={"Authorization": "Bearer test-client-token"},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "client_task_timeout"


async def test_careerpilot_api_client_submits_task() -> None:
    user_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer remote-token"
        assert request.headers["X-Request-ID"] == "req-remote"
        return httpx.Response(
            200,
            json={
                "request_id": "req-remote",
                "correlation_id": "corr-remote",
                "status": "success",
                "plan_id": "direct_helper",
                "summary": "ok",
                "steps": [],
                "output": {"value": 1},
                "error": None,
            },
            headers={"X-Request-ID": "req-remote"},
        )

    transport = httpx.MockTransport(handler)
    client = CareerPilotApiClient(
        base_url="http://careerpilot.test",
        api_token="remote-token",
        client=httpx.AsyncClient(transport=transport),
    )
    payload = await client.submit_client_task(
        user_id=str(user_id),
        intent="helper",
        parameters={"value": 1},
        correlation_id="corr-remote",
        request_id="req-remote",
    )
    assert payload["status"] == "success"


async def test_careerpilot_api_client_maps_api_errors() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            401,
            json={
                "error": {"code": "unauthorized", "message": "Client API authentication failed."},
                "request_id": "req-401",
            },
        )
    )
    client = CareerPilotApiClient(
        base_url="http://careerpilot.test",
        api_token="bad",
        client=httpx.AsyncClient(transport=transport),
    )
    try:
        await client.submit_client_task(user_id=str(uuid4()), intent="helper")
    except CareerPilotApiError as exc:
        assert exc.code == "unauthorized"
        assert exc.status_code == 401
    else:
        raise AssertionError("expected CareerPilotApiError")
