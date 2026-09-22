# ADR 0014: UUID primary keys and timezone-aware timestamps

## Status

Accepted

## Context

M1 introduces the first persisted entities. Naive datetimes and sequential
integer keys would complicate multi-region operation, idempotent ingest,
and client-generated identifiers later.

## Decision

- Entity identifiers are UUIDs generated at the application boundary via
  `IdGeneratorPort` (default UUID v4).
- All persisted timestamps are timezone-aware. `ClockPort` returns UTC.
- Domain factories reject naive datetimes.

## Consequences

- Tests inject frozen clocks and fixed IDs.
- PostgreSQL columns use `UUID` and `TIMESTAMPTZ`.
