# ADR 0007: Temporal for durable workflows

## Status

Accepted

## Context

Daily discovery, approvals, and later application submission need retries,
timeouts, idempotency, and recovery across process restarts. `asyncio.sleep`
and in-memory flags are not approval mechanisms.

## Decision

- Temporal is the durable workflow engine.
- M0 does not run a Temporal worker or Compose Temporal service.
- M5 search API is request/response application code (with ports).
- M8 introduces `DailyJobDiscoveryWorkflow` and the worker container.
- Workflows are deterministic; I/O is in activities.
- An in-process event bus is not a replacement for Temporal signaling.

## Consequences

- Operational surface increases at M8, not M0.
- Approval (M18) uses durable workflow state and signals.
