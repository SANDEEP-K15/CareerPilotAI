# ADR 0026: Hybrid semantic matching augments M7

## Status

Accepted

## Context

M14 adds LLM-based semantic assessment without replacing M7 deterministic
scoring, embeddings, vendor SDKs in application/domain, or changes to the
M7 `match_job` / `rank_matches` functions and M5–M13 surfaces.

## Decision

- `SemanticMatchingService` builds provider-neutral prompts from
  `CareerProfile`, canonical `Job`, and the M7 `JobMatch` baseline.
- The LLM must return JSON with `alignment_score` (0–100), `summary`, and
  `concerns`. Parsed output becomes `SemanticAnalysis`.
- `combine_match_scores` blends M7 score (70%) with semantic alignment
  (30%) when parsing succeeds; otherwise the M7 score is used unchanged.
- `SemanticMatchJobsUseCase` ranks with `rank_augmented_matches` using the
  combined score, then M7 score, then `job_id` for ties.
- LLM failures and malformed output fall back to deterministic-only results.
- Token/cost metadata flows through existing M13 `InvokeLlmUseCase` /
  `CostManagerPort`; CareerPilot does not fabricate costs or confidence.

## Consequences

- M7 HTTP matching and M8/M11 deterministic paths remain unchanged.
- Infrastructure LLM adapters can land later without altering the hybrid
  contract.
