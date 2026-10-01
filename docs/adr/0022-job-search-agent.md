# ADR 0022: Job Search Agent orchestrates existing search ingest

## Status

Accepted

## Context

M10 needs an agent entry point for job search without LLMs, new providers,
or changes to the M5 HTTP API or M4 ingest rules.

## Decision

- `JobSearchAgent` implements `AgentPort` with key `job_search`.
- It accepts structured `AgentInput` parameters (keywords, location,
  pagination, optional sources) and delegates to
  `SearchAndIngestJobsUseCase`.
- Results are canonical job snapshots plus per-source pages and normalized
  provider failures. Runtime exceptions are not leaked.
- The agent is registered explicitly by the composition root; the empty
  default registry remains valid.
- M5 `POST /api/v1/jobs/search` is unchanged.

## Consequences

- M11+ agents can compose `ExecuteAgentTaskUseCase` with `job_search`.
- LLM reasoning stays out of M10.
