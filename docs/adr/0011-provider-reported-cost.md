# ADR 0011: Provider-reported cost only

## Status

Accepted

## Context

LLM and search API spend must be observable without inventing numbers.

## Decision

- `CostManagerPort` (M13) records provider, model, request id when
  available, user, task, token counts when available, **actual** cost when
  the provider reports it, otherwise estimated tokens only or omitted cost.
- Never fabricate currency amounts.
- Cost tracking failure must not fail the business operation unless a
  specific policy requires it.

## Consequences

- Queryable ledger from M13. Not implemented in M0.
