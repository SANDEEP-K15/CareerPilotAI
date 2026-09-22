# ADR 0010: Explicit permissions

## Status

Accepted

## Context

Agents and LLMs must not perform consequential actions by implication.

## Decision

- Capabilities are an explicit permission set (for example SEARCH_JOBS,
  SUBMIT_APPLICATION). Exact enum lands with the features that need it.
- Agents and application services check permissions; they cannot grant
  them.
- LLM output never directly executes privileged actions.
- Production API access fails closed without authentication once user
  data exists (from M1/M5). M0 has no API.

## Consequences

- Approval (M18) is a separate durable control from permission checks.
- Tests can inject a permission set without an LLM.
