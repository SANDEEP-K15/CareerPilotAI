"""HTTP client for external interfaces calling CareerPilot APIs."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx

REQUEST_ID_HEADER = "X-Request-ID"


class CareerPilotApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.request_id = request_id


class CareerPilotApiClient:
    """Submit client tasks to CareerPilot. No business logic."""

    def __init__(
        self,
        *,
        base_url: str,
        api_token: str,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._owns_client = client is None

    async def submit_client_task(
        self,
        *,
        user_id: str,
        intent: str,
        parameters: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        body = {
            "user_id": user_id,
            "intent": intent,
            "parameters": parameters or {},
            "correlation_id": correlation_id,
        }
        headers = {
            "Authorization": f"Bearer {self._api_token}",
            "Accept": "application/json",
            REQUEST_ID_HEADER: request_id or str(uuid4()),
        }
        client = self._client or httpx.AsyncClient(timeout=self._timeout_seconds)
        try:
            try:
                response = await client.post(
                    f"{self._base_url}/api/v1/client/tasks",
                    json=body,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise CareerPilotApiError(
                    "CareerPilot API timed out.",
                    code="timeout",
                ) from exc
            except httpx.HTTPError as exc:
                raise CareerPilotApiError(
                    "CareerPilot API is unavailable.",
                    code="unavailable",
                ) from exc
            return _parse_response(response)
        finally:
            if self._owns_client:
                await client.aclose()


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    request_id = response.headers.get(REQUEST_ID_HEADER)
    try:
        payload = response.json()
    except ValueError as exc:
        raise CareerPilotApiError(
            "CareerPilot API returned malformed JSON.",
            code="malformed_response",
            status_code=response.status_code,
            request_id=request_id,
        ) from exc
    if not isinstance(payload, dict):
        raise CareerPilotApiError(
            "CareerPilot API returned an unexpected payload.",
            code="malformed_response",
            status_code=response.status_code,
            request_id=request_id,
        )
    if response.status_code >= 400:
        error = payload.get("error")
        if isinstance(error, dict):
            code = str(error.get("code", "api_error"))
            message = str(error.get("message", "CareerPilot API request failed."))
        else:
            code = "api_error"
            message = "CareerPilot API request failed."
        raise CareerPilotApiError(
            message,
            code=code,
            status_code=response.status_code,
            request_id=str(payload.get("request_id", request_id or "")) or request_id,
        )
    return payload
