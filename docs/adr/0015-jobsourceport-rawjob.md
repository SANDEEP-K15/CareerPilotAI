# ADR 0015: JobSourcePort returns RawJob pages, not persisted Job entities

## Status

Accepted

## Context

M1 introduced canonical `Job` as a persisted catalog entity with application
identity (`id`), `content_hash`, and `discovered_at`. Job providers return
listings that do not yet have those fields. Folding provider results into
`Job` at the port boundary would force adapters to invent IDs and hashes.

## Decision

- `JobSourcePort.search` returns `JobSearchPage` of `RawJob` values.
- `RawJob` is provider-neutral (source key, external id, title, company,
  URLs, location, description, posted_at, opaque extra).
- Canonical `Job` is unchanged and remains the persistence model.
- Mapping `RawJob` → `Job` is application ingest (`job_from_raw` +
  `IngestRawJobUseCase`; ADR 0016).
- Pagination is page/page_size/`has_more` only. Cursor schemes are not
  part of the contract until a provider requires them.
- Detail fetch is not on the port until a real adapter needs it.

## Consequences

- Application search can fan out across the registry without persisting.
- Adapters must not import `Job.new`.
- Tests use an in-memory `JobSourcePort`; no vendor is registered by default.
