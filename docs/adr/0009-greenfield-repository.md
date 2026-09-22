# ADR 0009: Greenfield repository

## Status

Accepted

## Context

The CareerPilot workspace started empty. A sibling project named
CareerPilotAI already mixed Tavily search, LLM ranking, Telegram identity,
and Temporal approval before a deterministic job pipeline existed.

## Decision

This repository is a greenfield CareerPilot. The sibling is reference
only. Patterns may be reused (ports, uv, Alembic, Temporal isolation).
Product shape follows this ADR set and the milestone plan, not the
sibling's agent-first slice.

## Consequences

- No copy-forward of sibling runtime as the trunk.
- Milestones M0–M8 are not skipped because later agent code already exists
  elsewhere.
