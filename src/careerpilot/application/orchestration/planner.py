from __future__ import annotations

from collections.abc import Mapping

from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.orchestration.errors import (
    InvalidOrchestrationPlanError,
    UnknownOrchestrationIntentError,
)
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.task_planner import ExecutionPlan, PlannedStep, UserTaskRequest

_SEARCH_AND_RANK_INTENTS = frozenset(
    {
        "search_and_rank",
        "search_then_rank",
        "discover_and_rank",
    }
)

_DEFAULT_AGENT_INTENTS: Mapping[str, str] = {
    "job_search": "search_jobs",
    "job_ranking": "rank",
}


class DeterministicTaskPlanner:
    """Rule-based planner. Maps intents to registered agents without LLM calls."""

    def __init__(self, *, registry: AgentRegistry) -> None:
        self._registered = {port.agent_key.value for port in registry.all()}

    def plan(self, request: UserTaskRequest) -> ExecutionPlan:
        intent = _normalize_intent(request.intent)
        if not intent:
            raise InvalidOrchestrationPlanError("intent is required.")
        explicit = request.parameters.get("steps")
        if explicit is not None:
            return _plan_from_explicit_steps(intent, explicit, self._registered)
        if intent in _SEARCH_AND_RANK_INTENTS:
            _require_agents(self._registered, ("job_search", "job_ranking"))
            return _search_and_rank_plan(intent, request.parameters)
        if intent in self._registered:
            return _direct_agent_plan(intent, request.parameters)
        raise UnknownOrchestrationIntentError(intent)


def _normalize_intent(raw: str) -> str:
    return AgentKey.parse(raw).value


def _direct_agent_plan(agent: str, parameters: Mapping[str, object]) -> ExecutionPlan:
    key = AgentKey.parse(agent)
    agent_intent = _agent_intent(key, parameters)
    step_params = {
        key_: value
        for key_, value in parameters.items()
        if key_ not in {"agent_intent", "steps"}
    }
    return ExecutionPlan(
        plan_id=f"direct_{key.value}",
        description=f"Run the {key.value} agent.",
        steps=(
            PlannedStep(
                step_id=key.value,
                agent=key,
                agent_intent=agent_intent,
                parameters=step_params,
            ),
        ),
    )


def _search_and_rank_plan(intent: str, parameters: Mapping[str, object]) -> ExecutionPlan:
    search_key = AgentKey.parse("job_search")
    rank_key = AgentKey.parse("job_ranking")
    shared = {
        key: value
        for key, value in parameters.items()
        if key not in {"agent_intent", "steps", "threshold", "limit", "job_ids"}
    }
    rank_params: dict[str, object] = {}
    if "threshold" in parameters:
        rank_params["threshold"] = parameters["threshold"]
    if "limit" in parameters:
        rank_params["limit"] = parameters["limit"]
    if "job_ids" in parameters:
        rank_params["job_ids"] = parameters["job_ids"]
    return ExecutionPlan(
        plan_id="search_and_rank",
        description="Search job sources, then rank ingested jobs for the user profile.",
        steps=(
            PlannedStep(
                step_id="search",
                agent=search_key,
                agent_intent="search_jobs",
                parameters=shared,
            ),
            PlannedStep(
                step_id="rank",
                agent=rank_key,
                agent_intent="rank",
                parameters=rank_params,
                inject_job_ids_from="search",
            ),
        ),
    )


def _plan_from_explicit_steps(
    intent: str,
    raw_steps: object,
    registered: set[str],
) -> ExecutionPlan:
    if not isinstance(raw_steps, (list, tuple)) or not raw_steps:
        raise InvalidOrchestrationPlanError("steps must be a non-empty list.")
    steps: list[PlannedStep] = []
    for index, item in enumerate(raw_steps):
        if not isinstance(item, Mapping):
            raise InvalidOrchestrationPlanError("each step must be a mapping.")
        agent_raw = item.get("agent")
        if not isinstance(agent_raw, str) or not agent_raw.strip():
            raise InvalidOrchestrationPlanError("each step requires an agent.")
        key = AgentKey.parse(agent_raw)
        if key.value not in registered:
            raise InvalidOrchestrationPlanError(
                f"step {index + 1} references unregistered agent '{key.value}'."
            )
        step_id = item.get("step_id")
        if step_id is None:
            step_id = f"step_{index + 1}"
        if not isinstance(step_id, str) or not step_id.strip():
            raise InvalidOrchestrationPlanError("step_id must be a non-empty string.")
        agent_intent = item.get("intent", "run")
        if not isinstance(agent_intent, str) or not agent_intent.strip():
            raise InvalidOrchestrationPlanError("intent must be a non-empty string.")
        parameters = item.get("parameters", {})
        if parameters is None:
            parameters = {}
        if not isinstance(parameters, Mapping):
            raise InvalidOrchestrationPlanError("parameters must be a mapping.")
        inject_from = item.get("inject_job_ids_from")
        if inject_from is not None and not isinstance(inject_from, str):
            raise InvalidOrchestrationPlanError("inject_job_ids_from must be a string.")
        steps.append(
            PlannedStep(
                step_id=step_id.strip(),
                agent=key,
                agent_intent=" ".join(agent_intent.split()),
                parameters=dict(parameters),
                inject_job_ids_from=inject_from.strip() if isinstance(inject_from, str) else None,
            )
        )
    plan_id = intent or "explicit"
    return ExecutionPlan(
        plan_id=plan_id,
        description="Execute an explicit multi-step plan.",
        steps=tuple(steps),
    )


def _require_agents(registered: set[str], agents: tuple[str, ...]) -> None:
    missing = [name for name in agents if name not in registered]
    if missing:
        joined = ", ".join(missing)
        raise InvalidOrchestrationPlanError(
            f"plan requires registered agent(s): {joined}."
        )


def _agent_intent(key: AgentKey, parameters: Mapping[str, object]) -> str:
    override = parameters.get("agent_intent")
    if override is not None:
        if not isinstance(override, str) or not override.strip():
            raise InvalidOrchestrationPlanError("agent_intent must be a non-empty string.")
        return " ".join(override.split())
    default = _DEFAULT_AGENT_INTENTS.get(key.value)
    if default is not None:
        return default
    return key.value
