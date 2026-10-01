from __future__ import annotations

from uuid import UUID

from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.agents.job_ranking.ranking import RankJobsQuery
from careerpilot.domain.matching import DEFAULT_LIMIT, DEFAULT_THRESHOLD
from careerpilot.ports.agent import AgentContext, AgentInput


def parse_rank_query(agent_input: AgentInput, user_id: UUID) -> RankJobsQuery:
    params = dict(agent_input.parameters)
    job_ids = _job_ids(params.get("job_ids"))
    threshold = _bounded_int(params.get("threshold"), default=DEFAULT_THRESHOLD, field="threshold")
    limit = _bounded_int(params.get("limit"), default=DEFAULT_LIMIT, field="limit")
    return RankJobsQuery(user_id=user_id, job_ids=job_ids, threshold=threshold, limit=limit)


def _job_ids(value: object) -> tuple[UUID, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise AgentExecutionError(
            "job_ids must be a list of UUID strings.",
            code="invalid_agent_task",
        )
    ids: list[UUID] = []
    seen: set[UUID] = set()
    for raw in value:
        if not isinstance(raw, (str, UUID)):
            raise AgentExecutionError(
                "job_ids must be a list of UUID strings.",
                code="invalid_agent_task",
            )
        job_id = raw if isinstance(raw, UUID) else UUID(str(raw).strip())
        if job_id in seen:
            continue
        seen.add(job_id)
        ids.append(job_id)
    return tuple(ids)


def _bounded_int(value: object, *, default: int, field: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentExecutionError(f"{field} must be an integer.", code="invalid_agent_task")
    return value


def require_user_id(context: AgentContext) -> UUID:
    if context.user_id is None:
        raise AgentExecutionError(
            "user_id is required in agent context.",
            code="invalid_agent_task",
        )
    return context.user_id
