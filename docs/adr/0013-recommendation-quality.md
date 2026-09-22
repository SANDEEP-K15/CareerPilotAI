# ADR 0013: Recommendation quality over quota

## Status

Accepted

## Context

A daily "top 20" that is padded with duplicates or weak matches is a
product failure.

## Decision

- Daily N is configurable (default 20).
- Return fewer than N when fewer jobs meet the relevance threshold.
- Explain that outcome. Never invent jobs.
- Deduplication must prevent duplicate daily recommendations.

## Consequences

- Matching and daily workflow (M7–M8) implement the threshold.
- Product copy reports "sufficiently relevant" counts, not fill rate.
