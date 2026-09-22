# ADR 0001: Hexagonal architecture / DDD layering

## Status

Accepted

## Context

CareerPilot must stay testable, provider-agnostic, and independent of any
single client. Business rules cannot live in Hermes, Telegram, FastAPI
routers, or vendor SDKs.

## Decision

Four layers; dependencies point inward:

- `careerpilot.domain` — entities, value objects, domain events, errors.
  Zero infrastructure imports. Canonical Job is provider-neutral.
- `careerpilot.application` — use cases and policies. Depends on domain
  and ports only.
- `careerpilot.ports` — interfaces (`JobSourcePort`, repositories, later
  LLM, workflow, cost, notifier, browser).
- `careerpilot.infrastructure` — adapters. The only layer that may import
  vendor SDKs and provider HTTP clients.

Delivery (`api`, `worker`) is thin: translate transport to use cases.

## Consequences

- New job providers are new infrastructure modules.
- New clients are new delivery adapters calling the same API/use cases.
- More files than a script; required for a production platform.
