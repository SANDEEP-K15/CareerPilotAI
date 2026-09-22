# ADR 0016: RawJob → canonical Job ingest is identity-keyed and idempotent

## Status

Accepted

## Context

M3 adapters emit `RawJob`. Canonical `Job` is the persistence entity with
`id`, `discovered_at`, and `content_hash`. Identity uniqueness already exists
as `(source, external_id)` on `jobs`. `content_hash` is a SHA-256 of
normalized title, company, description, and URLs.

## Decision

- Application `job_from_raw` maps any `RawJob` to `Job.new`. It is provider
  neutral: no vendor branches, no vendor fields on `Job`.
- Opaque `RawJob.extra` is copied into `Job.extra` (persisted as JSON
  metadata). That is the only place leftover provider keys may survive.
- `IngestRawJobUseCase` is the idempotent write path. `PersistJobUseCase`
  remains create-only and still raises `JobAlreadyExistsError`.
- Identity is `(source, external_id)` after whitespace normalization.
  Cross-source listings never merge, even with identical hashes.
- Outcomes:
  - **created** — no row for that identity
  - **unchanged** — identity exists and normalized fields are equivalent
    (hash, title, company, URLs, location, description, posted_at, extra,
    plus preserved status/remote/employment)
  - **updated** — identity exists and any of those fields differ; same `id`
    and `discovered_at`; `JobRepository.update`
  - **rejected** — `InvalidJobError` (missing required data, non-http URL);
    no write
- Naive `posted_at` is interpreted as UTC. Aware values convert with
  `astimezone(UTC)`. Missing timestamps stay missing.
- HTTP(S) URLs are canonicalized (scheme/host case, drop fragment, keep
  path and query). Source URL and application URL stay separate.
- Country/market of a provider search is adapter configuration, not a
  `Job` field. Location on a listing is whatever the source returned.

## Consequences

- Re-running the same ingest cannot insert a second `jobs` row.
- Hash is a change detector, not a second unique key.
- User profile / search-country selection is out of this milestone.
