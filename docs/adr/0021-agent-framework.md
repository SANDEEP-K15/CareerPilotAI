# ADR 0021: Provider-neutral agent framework

## Status

Accepted

## Context

M10+ agents must orchestrate application services without embedding LLM
vendors, job-provider names, or Temporal clients in domain logic.

## Decision

- `AgentPort` in ports defines `AgentInput`, `AgentOutput`, and
  `AgentContext` contracts.
- `AgentKey` is a normalized identifier, not a model name.
- `AgentRegistry` registers zero or more agents; duplicates and unknown
  lookups are application errors.
- `ExecuteAgentTaskUseCase` runs one task and returns `AgentRunResult`
  with success or structured failure codes.
- Agents raise `AgentExecutionError` for expected failures; unexpected
  exceptions are normalized without leaking internals.
- M9 ships no JobSearchAgent, RankingAgent, planner, executive, LLM
  adapter, or Hermes integration.

## Consequences

- M10–M12 add concrete agents behind the same port and registry.
- Deterministic business rules remain in domain/application use cases.
