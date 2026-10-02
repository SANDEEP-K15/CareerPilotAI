# ADR 0029: LLM application preparation package

## Status

Accepted

## Context

M17 prepares candidates for applications and interviews without submitting
applications (M20+) or browser automation (M19). Users need structured guidance
derived from profile, active resume, and a target job. Resume versions must
remain immutable (ADR 0018).

## Decision

- `ApplicationPreparationService` builds provider-neutral prompts from
  `CareerProfile`, canonical `Job`, and the user's active `Resume`.
- The LLM returns JSON with `guidance`, `talking_points`
  (`section`, `point`), and `interview_questions` (`question`, `focus`).
  Parsed output becomes `ApplicationPrepPackage`.
- `PrepareApplicationUseCase` loads user, profile, active resume, and job;
  it does not mutate resumes or submit applications.
- LLM failures and malformed output raise `ApplicationPreparationFailedError`
  (HTTP 503). No fabricated prep content.
- Usage/cost flows through M13 with task `application_preparation`.
- Expose `POST /api/v1/users/{user_id}/applications/prepare` with `{ "job_id" }`.

## Consequences

- Clients receive a prep package suitable for review before M18 approvals
  and M20 submission workflows.
- Cover letters, Telegram, new providers, and orchestration remain out of scope.
