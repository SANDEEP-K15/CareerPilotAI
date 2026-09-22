from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import (
    JobSearchPage,
    JobSearchQuery,
    JobSourceError,
    normalize_job_source_failure,
)


@dataclass(frozen=True, slots=True)
class SourceSearchSuccess:
    source: SourceKey
    page: JobSearchPage


@dataclass(frozen=True, slots=True)
class SourceSearchFailure:
    source: SourceKey
    error: JobSourceError


@dataclass(frozen=True, slots=True)
class MultiSourceSearchResult:
    successes: tuple[SourceSearchSuccess, ...]
    failures: tuple[SourceSearchFailure, ...]


class SearchRegisteredSourcesUseCase:
    """Search one or more registered sources. One failure does not abort others."""

    def __init__(self, *, registry: JobSourceRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        query: JobSearchQuery,
        *,
        sources: Sequence[str] | None = None,
    ) -> MultiSourceSearchResult:
        ports = self._registry.resolve(sources)
        successes: list[SourceSearchSuccess] = []
        failures: list[SourceSearchFailure] = []
        for port in ports:
            try:
                page = await port.search(query)
            except Exception as exc:
                error = normalize_job_source_failure(port.source_key.value, exc)
                failures.append(SourceSearchFailure(source=port.source_key, error=error))
                continue
            successes.append(SourceSearchSuccess(source=port.source_key, page=page))
        return MultiSourceSearchResult(
            successes=tuple(successes),
            failures=tuple(failures),
        )
