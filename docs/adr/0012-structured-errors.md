# ADR 0012: Structured domain and application errors

## Status

Accepted

## Context

Clients and operators need machine-readable failures. Stack traces and
"something went wrong" are not an error model.

## Decision

- Domain and application errors are typed, with a stable code and safe
  message.
- API mapping (later) translates to HTTP without internal traces.
- Provider failures are normalized at the adapter boundary
  (timeout, rate limit, unavailable, malformed).

## Consequences

- Error types are introduced with the first real use cases (M1+).
- M0 has no error taxonomy beyond this decision.
