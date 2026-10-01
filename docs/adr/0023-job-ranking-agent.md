# ADR 0023: Job Ranking Agent uses M7 matching

## Status

Accepted

## Context

M11 needs an agent that ranks a supplied set of canonical jobs for a user
without LLMs, duplicated scoring rules, or changes to the M7 matcher or
M5–M10 surfaces.

## Decision

- `JobRankingAgent` (`job_ranking`) implements `AgentPort`.
- `AgentContext.user_id` selects the persisted career profile.
- `AgentInput.parameters.job_ids` lists canonical jobs to rank (may be
  empty). Unknown ids are skipped.
- Ranking calls `rank_matches` from `domain.matching` via
  `rank_jobs_for_profile`; threshold/limit validation reuses
  `InvalidMatchQueryError` codes from M7.
- Output includes scores, matched/missing skills, reasons, and concerns.
- Order is `-score`, then `job_id` string (M7).

## Consequences

- Planner/executive agents can chain search then rank without new scoring
  code.
- LLM ranking remains out of scope.
