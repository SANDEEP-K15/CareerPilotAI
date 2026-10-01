from __future__ import annotations

from careerpilot.application.agents.execution import ExecuteAgentTaskUseCase
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.application.orchestration.planner import DeterministicTaskPlanner
from careerpilot.application.orchestration.results import (
    OrchestrationResult,
    OrchestrationStatus,
    OrchestrationStepResult,
)
from careerpilot.application.orchestration.router import TaskRouter
from careerpilot.ports.agent import AgentOutput
from careerpilot.ports.task_planner import TaskPlannerPort, UserTaskRequest


class Executive:
    """Plans multi-step work, routes steps to agents, and aggregates results."""

    def __init__(
        self,
        *,
        planner: TaskPlannerPort,
        router: TaskRouter,
        executor: ExecuteAgentTaskUseCase,
    ) -> None:
        self._planner = planner
        self._router = router
        self._executor = executor

    async def run(self, request: UserTaskRequest) -> OrchestrationResult:
        intent = " ".join(request.intent.split())
        plan = self._planner.plan(
            UserTaskRequest(
                intent=intent,
                parameters=request.parameters,
                context=request.context,
            )
        )
        prior: dict[str, AgentOutput] = {}
        step_results: list[OrchestrationStepResult] = []
        for step in plan.steps:
            task = self._router.build_task(step, context=request.context, prior_outputs=prior)
            result = await self._executor.execute(task)
            step_results.append(
                OrchestrationStepResult(step_id=step.step_id, agent=step.agent, result=result)
            )
            if not result.succeeded:
                return OrchestrationResult(
                    status=OrchestrationStatus.FAILED,
                    intent=intent,
                    plan_id=plan.plan_id,
                    summary=f"Orchestration failed at step '{step.step_id}'.",
                    steps=tuple(step_results),
                    error_code=result.error_code,
                    error_message=result.error_message,
                )
            if result.output is not None:
                prior[step.step_id] = result.output
        final = step_results[-1].result.output if step_results else None
        return OrchestrationResult(
            status=OrchestrationStatus.SUCCESS,
            intent=intent,
            plan_id=plan.plan_id,
            summary=_success_summary(plan.description, len(step_results)),
            steps=tuple(step_results),
            output=final,
        )


def build_executive(*, registry: AgentRegistry) -> Executive:
    """Composition helper for tests and future delivery layers."""
    executor = ExecuteAgentTaskUseCase(registry=registry)
    return Executive(
        planner=DeterministicTaskPlanner(registry=registry),
        router=TaskRouter(registry=registry),
        executor=executor,
    )


def _success_summary(description: str, step_count: int) -> str:
    if step_count <= 1:
        return description
    return f"{description} Completed {step_count} step(s)."
