# ADR 0005: First JobSource validation adapter

## Status

Accepted

## Context

M3 needs one real, legally accessible HTTP job API to prove the port,
normalization, and failure handling. That first adapter must not be
mistaken for the product or for a guaranteed primary source.

## Decision

- The first concrete `JobSourcePort` implementation used for **validation**
  will be Adzuna (documented REST search API, credential-gated).
- Adzuna is **not** a hard dependency of CareerPilot.
- Adzuna is **not** the guaranteed primary source of jobs.
- Domain, application services, `JobSourcePort`, and the registry remain
  completely provider-neutral.
- The application must boot and be testable with Adzuna unset or disabled.
- Subsequent providers (for example The Muse, Greenhouse board APIs,
  Lever board APIs) must plug in without modifying domain or application
  logic.
- Without credentials, the adapter reports unavailability. It must not
  return fabricated jobs.

## Consequences

- M3 adds `infrastructure/jobsources/adzuna/` (or equivalent) only.
- Tests for matching, dedupe, and daily recommendations use fakes, not
  Adzuna.
- Docs and config treat Adzuna as optional.
