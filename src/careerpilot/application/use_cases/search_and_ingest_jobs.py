from __future__ import annotations

from dataclasses import dataclass

from careerpilot.application.job_sources.search import (
    SearchRegisteredSourcesUseCase,
    SourceSearchFailure,
)
from careerpilot.application.jobs.ingest_types import IngestOutcome
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import InvalidJobSearchQueryError, JobSearchQuery


@dataclass(frozen=True, slots=True)
class SearchJobsCommand:
    keywords: tuple[str, ...] = ()
    location: str | None = None
    remote_only: bool | None = None
    page: int = 1
    page_size: int = 20
    sources: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class SourcePageSummary:
    source: SourceKey
    page: int
    page_size: int
    returned: int
    has_more: bool


@dataclass(frozen=True, slots=True)
class SearchAndIngestResult:
    jobs: tuple[Job, ...]
    page: int
    page_size: int
    has_more: bool
    sources: tuple[SourcePageSummary, ...]
    failures: tuple[SourceSearchFailure, ...]


class SearchAndIngestJobsUseCase:
    """Search registered sources, ingest RawJob pages, return canonical Jobs."""

    def __init__(
        self,
        *,
        search_sources: SearchRegisteredSourcesUseCase,
        ingest: IngestRawJobUseCase,
    ) -> None:
        self._search_sources = search_sources
        self._ingest = ingest

    async def execute(self, command: SearchJobsCommand) -> SearchAndIngestResult:
        if command.sources is not None and len(command.sources) == 0:
            raise InvalidJobSearchQueryError("sources must not be empty when provided.")
        query = JobSearchQuery(
            keywords=command.keywords,
            location=command.location,
            remote_only=command.remote_only,
            page=command.page,
            page_size=command.page_size,
        )
        searched = await self._search_sources.execute(query, sources=command.sources)
        jobs: list[Job] = []
        summaries: list[SourcePageSummary] = []
        for success in searched.successes:
            ingested = 0
            for raw in success.page.items:
                result = await self._ingest.execute(raw)
                if result.outcome is IngestOutcome.REJECTED or result.job is None:
                    continue
                jobs.append(result.job)
                ingested += 1
            summaries.append(
                SourcePageSummary(
                    source=success.source,
                    page=success.page.page,
                    page_size=success.page.page_size,
                    returned=ingested,
                    has_more=success.page.has_more,
                )
            )
        return SearchAndIngestResult(
            jobs=tuple(jobs),
            page=query.page,
            page_size=query.page_size,
            has_more=any(item.has_more for item in summaries),
            sources=tuple(summaries),
            failures=searched.failures,
        )
