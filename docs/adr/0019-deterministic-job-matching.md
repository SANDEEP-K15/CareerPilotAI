# ADR 0019: Deterministic matching uses integer weighted scores

## Status

Accepted

## Context

M7 must rank persisted jobs against a career profile without LLMs or
embeddings. Opaque scores would block explanation and tests.

## Decision

- Hard filters run first: inactive jobs, incompatible remote policy,
  incompatible employment type, and non-remote location mismatch when both
  sides specified a location.
- Unspecified values never hard-filter.
- Score is an integer 0–100: skills 40, title 30, location 15, remote 10,
  employment 5. Arithmetic is integer-only.
- Skills match as casefolded substrings of job title/description against
  profile skills. Resume text is not parsed.
- Results below a threshold are omitted (default 40). Return fewer than
  `limit` rather than pad. Ties break on `job_id` string order.
- Matching reads `JobRepository.list_active` and the user's profile. It
  does not call `JobSourcePort`.

## Consequences

- M8 can snapshot these scores into daily recommendations.
- Semantic matching remains M14.
