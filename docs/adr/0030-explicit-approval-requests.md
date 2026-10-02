# ADR 0030: Explicit human approval requests

## Status

Accepted

## Context

Consequential actions such as job application submission (M20) require a
durable human decision separate from permissions (ADR 0010) and from LLM
output. Approval must not imply execution.

## Decision

- Model `ApprovalRequest` with `ApprovalAction` and `ApprovalStatus`
  (`pending`, `approved`, `rejected`, `expired`).
- Link each request to `user_id`, `job_id`, and `action`. Default TTL seven
  days; optional explicit `expires_at` on create.
- Deterministic transitions: approve/reject only from non-expired `pending`;
  time-based expiration persists `expired` on read when past `expires_at`.
- At most one stored `pending` row per `(user_id, job_id, action)`.
- HTTP: create, list, get, approve, reject under `/api/v1/users/{user_id}/approval-requests`.
- Granting approval records intent only; M20+ must check approval before any
  submit automation and still perform execution explicitly.

## Consequences

- Provider-neutral persistence (PostgreSQL + in-memory tests).
- No browser automation, Telegram, or submission in M18.
