"""Job search agent. Orchestrates SearchAndIngestJobsUseCase only."""

from __future__ import annotations

from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.agents.job_search.parsing import parse_search_command
from careerpilot.application.agents.job_search.present import job_search_agent_output
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import (
    SearchAndIngestJobsUseCase,
)
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.job_source import InvalidJobSearchQueryError
from careerpilot.ports.repositories import JobRepository

JOB_SEARCH_AGENT_KEY = AgentKey.parse("job_search")


class JobSearchAgent:
    """Search registered job sources and ingest canonical jobs via M4."""

    def __init__(self, *, search: SearchAndIngestJobsUseCase) -> None:
        self._search = search

    @property
    def agent_key(self) -> AgentKey:
        return JOB_SEARCH_AGENT_KEY

    @property
    def description(self) -> str:
        return "Search registered job sources and ingest canonical job listings."

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        del context
        command = parse_search_command(agent_input)
        try:
            result = await self._search.execute(command)
        except InvalidJobSearchQueryError as exc:
            raise AgentExecutionError(exc.message, code=exc.code) from exc
        return job_search_agent_output(result)


def build_job_search_agent(
    *,
    registry: JobSourceRegistry,
    jobs: JobRepository,
    clock: ClockPort,
    ids: IdGeneratorPort,
) -> JobSearchAgent:
    """Composition helper for worker/API wiring and tests."""
    return JobSearchAgent(
        search=SearchAndIngestJobsUseCase(
            search_sources=SearchRegisteredSourcesUseCase(registry=registry),
            ingest=IngestRawJobUseCase(jobs=jobs, clock=clock, ids=ids),
        )
    )


__all__ = ["JOB_SEARCH_AGENT_KEY", "JobSearchAgent", "build_job_search_agent"]
