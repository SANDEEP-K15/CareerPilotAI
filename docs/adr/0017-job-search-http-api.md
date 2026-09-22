# ADR 0017: Versioned job-search HTTP API returns canonical Jobs

## Status

Accepted

## Context

M4 ingest persists canonical `Job` rows from `RawJob`. Clients need an HTTP
entry point. FastAPI must stay in the delivery layer. Providers stay behind
`JobSourcePort`. Source market (for example a country code on an adapter)
is configuration, not an API or Job field.

## Decision

- Expose `POST /api/v1/jobs/search`.
- Request fields are `JobSearchQuery` plus optional explicit `sources`.
- The handler calls `SearchAndIngestJobsUseCase` only.
- Responses are canonical Job DTOs. `RawJob`, ORM models, and vendor
  payloads are not HTTP types. Opaque `extra` is not serialized.
- Unknown registered-source names are `404 unknown_job_source`.
- Provider failures are listed on a `200` response so other sources remain.
- `X-Request-ID` is accepted or generated; no broader observability stack.

## Consequences

- New providers are registry registrations, not API changes.
- Empty registry is a valid deployment; the API does not invent a default
  vendor or country.
