# ADR 0027: Client task HTTP API for external interfaces

## Status

Accepted

## Context

ADR 0008 requires Hermes (and other UIs) to stay clients of CareerPilot.
M12 provides deterministic orchestration via `Executive`. External clients need
an authenticated HTTP boundary to submit user tasks without duplicating
orchestration or embedding business logic in Hermes.

## Decision

- Expose `POST /api/v1/client/tasks` (provider-neutral path; Hermes is one client).
- Authenticate with `Authorization: Bearer` using `CLIENT__API_TOKEN`.
- Accept optional `correlation_id` in the body; echo `request_id` and
  `correlation_id` on responses. Reuse `X-Request-ID` middleware.
- Map requests to `SubmitClientTaskUseCase`, which wraps M12 `Executive` only.
- Return structured success and orchestration failure bodies (`200` with
  `status: failed` for agent/orchestration failures). Use `504` /
  `503` for timeout and missing wiring respectively.
- Provide `CareerPilotApiClient` in infrastructure for outbound calls from
  Hermes-side code. No Telegram or LLM behavior in this milestone.

## Consequences

- Hermes integrates by HTTP only; CareerPilot owns orchestration.
- Staging and production require `CLIENT__API_TOKEN` alongside production secrets.
- New client capabilities extend agents and plans, not duplicate routers.
