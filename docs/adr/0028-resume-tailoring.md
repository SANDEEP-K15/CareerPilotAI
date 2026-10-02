# ADR 0028: LLM resume tailoring without mutating versions

## Status

Accepted

## Context

M6 stores immutable resume versions with one active row per user (ADR 0018).
M16 adds job-specific tailoring for applications. Overwriting stored resume
content would break auditability and matching history.

## Decision

- `ResumeTailoringService` builds provider-neutral prompts from
  `CareerProfile`, canonical `Job`, and the user's **active** `Resume`.
- The LLM returns JSON with `tailored_content` (full text) and `changes`
  (array of `{section, description}`). Parsed output becomes
  `ResumeTailoringResult` in the domain layer.
- `TailorResumeUseCase` loads user, profile, active resume, and job; it
  never calls `AddResumeVersionUseCase` or updates repository rows.
- LLM failures and malformed output raise `ResumeTailoringFailedError` (HTTP
  503). No silent fallback resume text.
- Token/cost metadata flows through M13 `InvokeLlmUseCase` / `CostManagerPort`
  with task `resume_tailoring`.
- Expose `POST /api/v1/users/{user_id}/resumes/tailor` with `{ "job_id" }`.

## Consequences

- Clients receive tailored text and a change summary; persisting a new version
  remains an explicit M6 resume write when product requires it.
- No cover letters, browser automation, or orchestration changes in M16.
