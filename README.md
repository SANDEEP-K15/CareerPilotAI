# CareerPilot AI

CareerPilot AI is an AI-powered career intelligence and job automation
platform. It discovers relevant jobs, evaluates fit against a user's career
profile, and eventually helps prepare applications while keeping human
approval as a hard boundary for consequential actions.

This repository is the product. Hermes, Telegram, web, and CLI clients are
interfaces. They must not contain CareerPilot business logic.

## Current milestone

**M4 — Normalization and deterministic deduplication.**

Not yet implemented: search API, matching, agents, Temporal workers, LLM
adapters, Hermes, resumes, or applications.

`IngestRawJobUseCase` maps provider-neutral `RawJob` values to canonical
`Job` rows. Identity is `(source, external_id)`. See ADR 0016.

Adzuna remains optional. Country for that adapter is `ADZUNA__COUNTRY`
(default `gb`) and is search configuration, not a field on `Job`.
See [Adzuna notes](docs/providers/adzuna.md).

## Principles

- Deterministic software for deterministic work. AI only where reasoning
  or semantic matching adds value.
- Job discovery is provider-neutral. `JobSourcePort` and the registry are
  the product boundary. Adzuna may later be the first adapter used to
  *validate* that boundary; it is not a platform dependency and not the
  guaranteed source of jobs.
- Never fabricate jobs, costs, or provider capabilities.
- Schema changes go through Alembic. Do not use `create_all()`.

## Local development

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, Python 3.12+.

```bash
uv sync --dev
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
uv run alembic -c database/alembic.ini upgrade head
uv run pytest
uv run ruff check .
uv run mypy
```

Integration tests run against local Postgres when it is reachable. They
skip automatically if Postgres is down, unless `CAREERPILOT_RUN_INTEGRATION=1`
is set (then missing Postgres is a failure).

## Layout

```
src/careerpilot/
  domain/            Canonical User and Job — provider-neutral
  application/       Use cases against repository ports
  ports/             Clock, IDs, repositories (JobSourcePort in M2)
  infrastructure/    Postgres adapters; optional Adzuna JobSourcePort
  config/            pydantic-settings
  api/               FastAPI delivery (later)
  worker/            Temporal worker (later)
database/            Alembic migrations
tests/               Unit, integration, and contract tests
```

## Documentation

- [Implementation plan](docs/implementation-plan.md)
- [Architecture](docs/architecture/overview.md)
- [ADRs](docs/adr/)
- [Adzuna provider](docs/providers/adzuna.md)
- [Database](database/README.md)

## License

Proprietary — all rights reserved.
