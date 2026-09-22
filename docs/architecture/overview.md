# Architecture overview

CareerPilot AI is the career intelligence backend. Clients (REST, web,
CLI, Hermes/Telegram, future surfaces) call versioned HTTP APIs. Hermes
must never own domain logic. Removing Hermes must not disable the product.

## Layering

Dependencies point inward only.

```
apps / api / worker
        ↓
application (use cases)
        ↓
domain  ←  ports (interfaces)
        ↑
infrastructure (adapters: job sources, Postgres, Temporal, LLM, …)
```

- **domain** — entities, value objects, domain events, errors. No
  frameworks. No provider schemas. M1 entities: `User` (identity) and
  canonical `Job` (catalog; not user-owned). `SourceKey` is a generic
  origin identifier, not a vendor enum.
- **application** — use cases and policies. Depends on domain
  and ports only.
- **ports** — repositories, clocks, and `JobSourcePort`. Search returns
  `RawJob` pages. Application ingest maps those to persisted `Job` rows
  (ADR 0015, ADR 0016).
- **infrastructure** — SQLAlchemy/Postgres adapters and system clock.
  Schema is applied only by Alembic. Optional Adzuna HTTP adapter lives
  under `infrastructure/jobsources/adzuna/` and is not auto-registered.
- **application** — use cases and the in-process `JobSourceRegistry`.
  Vendor names are not hard-coded. One source failure does not abort
  other registered sources.
- **config** — environment-backed settings. Production/staging reject a
  placeholder `SECURITY__SECRET_KEY`.
- **api / worker** — delivery. FastAPI under `/api/v1` (ADR 0017).
  Workers remain later.

## Persistence (M1, M6)

Tables: `users`, `jobs`, `career_profiles`, `resumes`. Unique
`(source, external_id)` on jobs. One profile per user. Unique
`(user_id, version)` on resumes, with at most one active resume per user.
Indexes on job `content_hash`, `posted_at`, and `status`. No Redis. No
match, recommendation, application, or cost tables yet.

## Job discovery

Job discovery is a subsystem, not a scraper and not a single vendor.

```
Use case → JobSourceRegistry → N adapters implementing JobSourcePort
                ↓
         normalized errors + RawJob
                ↓
         Normalizer → canonical Job
                ↓
         deterministic dedupe / filter / match / rank
```

No job provider is a platform dependency. The registry must operate when
zero, one, or many adapters are configured. One unavailable source must
not abort the whole search when others succeed (from M5/M8).

**Adzuna** is the first *validation* adapter (M3). It is not the product
goal, not a required runtime, and not allowed to leak into domain or
application code.

AI agents (M9+) orchestrate reasoning through application services. They
do not implement SQL, provider HTTP, or Temporal clients.

## First production slice (M1–M8)

User/profile foundation, job source abstraction, at least one real
adapter for validation, normalize, persist, dedupe, search API,
deterministic matching, daily recommendation workflow, tests,
observability, docs.

## Durable work

Temporal is the workflow engine from M8. Workflows stay deterministic;
I/O lives in activities. An in-process event bus is not a substitute.

## Safety

Submitting applications, sending recruiter messages, or changing
externally visible data requires durable human approval (M18+). LLM
output cannot grant permissions or execute privileged actions.

## Related documents

- [Implementation plan](../implementation-plan.md)
- [ADR index](../adr/README.md)
