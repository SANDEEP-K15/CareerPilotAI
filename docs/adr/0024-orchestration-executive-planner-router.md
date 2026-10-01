# ADR 0024: Deterministic executive, planner, and task router

## Status

Accepted

## Context

M12 needs provider-neutral orchestration that accepts user tasks, plans
multi-step work, routes steps to registered agents, and executes them
through the M9 agent framework without LLM vendors or changes to M5–M11
behavior.

## Decision

- `UserTaskRequest`, `ExecutionPlan`, and `PlannedStep` live in
  `ports/task_planner.py` with a `TaskPlannerPort` contract.
- `DeterministicTaskPlanner` maps normalized intents to plans:
  - direct invocation when the intent matches a registered `AgentKey`
  - composite `search_and_rank` (and aliases) chaining `job_search` then
    `job_ranking`, injecting `job_ids` from the search step
  - optional explicit `parameters.steps` for test and future clients
- `TaskRouter` validates registry membership and builds `AgentTask` values,
  including prior-step `job_ids` wiring.
- `Executive` runs plans sequentially via `ExecuteAgentTaskUseCase` and
  returns `OrchestrationResult` with per-step `AgentRunResult` entries.
- Failures stop the plan and surface structured error codes; no LLM calls.

## Consequences

- M13 can supply an LLM-backed `TaskPlannerPort` without changing the
  executive or router.
- M5–M11 APIs, agents, ingest, and matching behavior stay unchanged.
