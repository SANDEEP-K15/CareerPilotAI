from __future__ import annotations

from collections.abc import Mapping

from careerpilot.application.agents.errors import UnknownAgentError
from careerpilot.application.agents.execution import AgentTask
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.orchestration.errors import InvalidOrchestrationPlanError
from careerpilot.ports.agent import AgentContext, AgentInput, AgentOutput
from careerpilot.ports.task_planner import PlannedStep


class TaskRouter:
    """Resolve planned steps to executable agent tasks against the registry."""

    def __init__(self, *, registry: AgentRegistry) -> None:
        self._registry = registry

    def build_task(
        self,
        step: PlannedStep,
        *,
        context: AgentContext,
        prior_outputs: Mapping[str, AgentOutput],
    ) -> AgentTask:
        try:
            self._registry.get(step.agent)
        except UnknownAgentError as exc:
            raise InvalidOrchestrationPlanError(
                f"agent '{step.agent.value}' is not registered."
            ) from exc
        parameters = dict(step.parameters)
        if step.inject_job_ids_from is not None:
            prior = prior_outputs.get(step.inject_job_ids_from)
            if prior is None:
                raise InvalidOrchestrationPlanError(
                    f"step '{step.step_id}' expects output from '{step.inject_job_ids_from}'."
                )
            job_ids = prior.data.get("job_ids")
            if not isinstance(job_ids, list):
                raise InvalidOrchestrationPlanError(
                    f"step '{step.inject_job_ids_from}' did not produce job_ids."
                )
            if "job_ids" not in parameters:
                parameters["job_ids"] = list(job_ids)
            else:
                parameters["job_ids"] = _merge_job_ids(parameters["job_ids"], job_ids)
        intent = " ".join(step.agent_intent.split())
        if not intent:
            raise InvalidOrchestrationPlanError(f"step '{step.step_id}' requires an intent.")
        return AgentTask(
            agent=step.agent,
            agent_input=AgentInput(intent=intent, parameters=parameters),
            context=context,
        )


def _merge_job_ids(existing: object, discovered: list[object]) -> list[object]:
    if not isinstance(existing, list):
        raise InvalidOrchestrationPlanError("job_ids must be a list when provided.")
    merged: list[object] = []
    seen: set[str] = set()
    for raw in (*existing, *discovered):
        token = str(raw).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        merged.append(raw)
    return merged
