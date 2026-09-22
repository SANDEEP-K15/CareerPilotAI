from __future__ import annotations

import logging
from typing import Any

import httpx

from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.jobsources.adzuna.mapper import ADZUNA_SOURCE_KEY, map_search_page
from careerpilot.infrastructure.jobsources.adzuna.settings import AdzunaSettings
from careerpilot.ports.job_source import (
    JobSearchPage,
    JobSearchQuery,
    JobSourceCapabilities,
    JobSourceError,
    JobSourceErrorCode,
)

logger = logging.getLogger(__name__)

_SOURCE = ADZUNA_SOURCE_KEY.value


class AdzunaJobSource:
    """Optional JobSourcePort adapter for Adzuna's documented search API."""

    def __init__(
        self,
        settings: AdzunaSettings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._owns_client = client is None

    @property
    def source_key(self) -> SourceKey:
        return ADZUNA_SOURCE_KEY

    @property
    def capabilities(self) -> JobSourceCapabilities:
        return JobSourceCapabilities(
            supports_search=True,
            supports_pagination=True,
            requires_credentials=True,
        )

    async def search(self, query: JobSearchQuery) -> JobSearchPage:
        if not self._settings.credentials_configured:
            raise JobSourceError(
                "Adzuna credentials are not configured.",
                code=JobSourceErrorCode.UNAVAILABLE,
                source=_SOURCE,
                retryable=False,
            )
        client = self._client or httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        try:
            return await self._search(client, query)
        finally:
            if self._owns_client:
                await client.aclose()

    async def _search(self, client: httpx.AsyncClient, query: JobSearchQuery) -> JobSearchPage:
        url = f"{self._settings.base_url}/jobs/{self._settings.country}/search/{query.page}"
        params = self._query_params(query)
        try:
            response = await client.get(url, params=params, headers={"Accept": "application/json"})
        except httpx.TimeoutException as exc:
            raise JobSourceError(
                "Adzuna request timed out.",
                code=JobSourceErrorCode.TIMEOUT,
                source=_SOURCE,
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise JobSourceError(
                "Adzuna is unavailable.",
                code=JobSourceErrorCode.UNAVAILABLE,
                source=_SOURCE,
                retryable=True,
            ) from exc

        logger.info("adzuna_http_response status_code=%s source=%s", response.status_code, _SOURCE)
        error = _error_for_status(response.status_code)
        if error is not None:
            raise error

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise JobSourceError(
                "Adzuna returned a malformed response.",
                code=JobSourceErrorCode.MALFORMED_RESPONSE,
                source=_SOURCE,
                retryable=False,
            ) from exc

        try:
            return map_search_page(payload, page=query.page, page_size=query.page_size)
        except ValueError as exc:
            raise JobSourceError(
                "Adzuna returned a malformed response.",
                code=JobSourceErrorCode.MALFORMED_RESPONSE,
                source=_SOURCE,
                retryable=False,
            ) from exc

    def _query_params(self, query: JobSearchQuery) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "app_id": self._settings.app_id.get_secret_value(),
            "app_key": self._settings.app_key.get_secret_value(),
            "results_per_page": query.page_size,
        }
        what = " ".join(query.keywords)
        if what:
            params["what"] = what
        if query.location is not None:
            params["where"] = query.location
        # remote_only is ignored: Adzuna's documented search API has no remote filter.
        return params


def _error_for_status(status_code: int) -> JobSourceError | None:
    if status_code in {401, 403}:
        return JobSourceError(
            "Adzuna rejected the request credentials.",
            code=JobSourceErrorCode.UNAUTHORIZED,
            source=_SOURCE,
            retryable=False,
        )
    if status_code == 429:
        return JobSourceError(
            "Adzuna rate limit exceeded.",
            code=JobSourceErrorCode.RATE_LIMITED,
            source=_SOURCE,
            retryable=True,
        )
    if status_code == 408:
        return JobSourceError(
            "Adzuna request timed out.",
            code=JobSourceErrorCode.TIMEOUT,
            source=_SOURCE,
            retryable=True,
        )
    if status_code >= 500:
        return JobSourceError(
            "Adzuna is unavailable.",
            code=JobSourceErrorCode.UNAVAILABLE,
            source=_SOURCE,
            retryable=True,
        )
    if status_code != 200:
        return JobSourceError(
            "Adzuna returned an unexpected error.",
            code=JobSourceErrorCode.UNKNOWN,
            source=_SOURCE,
            retryable=False,
        )
    return None
