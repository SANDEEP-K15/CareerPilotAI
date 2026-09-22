# ADR 0006: Hybrid matching; LLM ranking later

## Status

Accepted

## Context

Opaque LLM scores are not an acceptable product contract. Many matching
dimensions are deterministic.

## Decision

Matching is a pipeline: hard filters → feature extraction → deterministic
score → optional semantic/LLM reasoning (M14) → rank → recommendations.

Each recommendation should eventually explain why it matched, overlapping
and missing skills, concerns, source, and application URL.

LLM ranking is not part of M0–M8.

## Consequences

- M7 can ship without an LLM provider.
- Quality evaluation is separate from unit tests (M21).
