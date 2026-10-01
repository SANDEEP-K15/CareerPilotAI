"""Job ranking agent. Orchestrates M7 deterministic matching only."""

from __future__ import annotations

from uuid import UUID

from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.agents.job_ranking.parsing import parse_rank_query, require_user_id
from careerpilot.application.agents.job_ranking.present import job_ranking_agent_output
from careerpilot.application.agents.job_ranking.ranking import rank_jobs_for_profile
from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.application.use_cases.match_jobs import InvalidMatchQueryError
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput
from careerpilot.ports.repositories import CareerProfileRepository, JobRepository

JOB_RANKING_AGENT_KEY = AgentKey.parse("job_ranking")


class JobRankingAgent:
    """Rank persisted jobs for a user's career profile using M7 matching."""

    def __init__(
        self,
        *,
        profiles: CareerProfileRepository,
        jobs: JobRepository,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs

    @property
    def agent_key(self) -> AgentKey:
        return JOB_RANKING_AGENT_KEY

    @property
    def description(self) -> str:
        return "Rank canonical jobs against a career profile with deterministic scores."

    async def run(self, agent_input: AgentInput, context: AgentContext) -> AgentOutput:
        user_id = require_user_id(context)
        query = parse_rank_query(agent_input, user_id)
        profile = await self._profiles.get_by_user_id(query.user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(query.user_id))
        catalog = await self._load_jobs(query.job_ids)
        try:
            matches, considered, rejected = rank_jobs_for_profile(
                profile,
                catalog,
                threshold=query.threshold,
                limit=query.limit,
            )
        except InvalidMatchQueryError as exc:
            raise AgentExecutionError(exc.message, code=exc.code) from exc
        return job_ranking_agent_output(
            threshold=query.threshold,
            limit=query.limit,
            considered=considered,
            rejected=rejected,
            matches=matches,
        )

    async def _load_jobs(self, job_ids: tuple[UUID, ...]) -> tuple[Job, ...]:
        loaded: list[Job] = []
        seen: set[UUID] = set()
        for job_id in job_ids:
            if job_id in seen:
                continue
            seen.add(job_id)
            job = await self._jobs.get_by_id(job_id)
            if job is not None:
                loaded.append(job)
        return tuple(loaded)


def build_job_ranking_agent(
    *,
    profiles: CareerProfileRepository,
    jobs: JobRepository,
) -> JobRankingAgent:
    return JobRankingAgent(profiles=profiles, jobs=jobs)


__all__ = ["JOB_RANKING_AGENT_KEY", "JobRankingAgent", "build_job_ranking_agent"]
