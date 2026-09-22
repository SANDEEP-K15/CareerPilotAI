# CareerPilot AI

CareerPilot AI is an AI-powered career intelligence and job automation
platform. It discovers relevant jobs, evaluates fit against a user's career
profile, and eventually helps prepare applications while keeping human
approval as a hard boundary for consequential actions.

This repository is the product. Hermes, Telegram, web, and CLI clients are
interfaces. They must not contain CareerPilot business logic.

## Current milestone

**M0 — Architecture and repository foundation** (this commit).

Not yet implemented: domain persistence, job providers, search, matching,
agents, Temporal workers, LLM adapters, Hermes, resumes, or applications.

## Principles

- Deterministic software for deterministic work. AI only where reasoning
  or semantic matching adds value.
- Job discovery is provider-neutral. `JobSourcePort` and the registry are
  the product boundary. Adzuna may be the first adapter used to *validate*
  that boundary; it is not a platform dependency and not the guaranteed
  source of jobs.
- Never fabricate jobs, costs, or provider capabilities.

## Local development

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, Python 3.12+.

```bash
uv sync --dev
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
uv run pytest
uv run ruff check .
uv run mypy
```

Postgres is available for later milestones. M0 does not run migrations or
an API server.

## Layout

```
src/careerpilot/     Application package (skeleton in M0)
  domain/            Canonical domain — provider-neutral
  application/       Use cases — provider-neutral
  ports/             Interfaces including future JobSourcePort
  infrastructure/    Adapters only (no concrete job source in M0)
  api/               FastAPI delivery (later)
  worker/            Temporal worker (later)
tests/               Unit, integration, and contract tests
evaluation/          AI evaluation (not unit tests; not implemented)
docs/                Architecture, ADRs, implementation plan
docker/              Compose (PostgreSQL only in M0)
```

## Documentation

- [Implementation plan](docs/implementation-plan.md)
- [Architecture](docs/architecture/overview.md)
- [ADRs](docs/adr/)

## License

Proprietary — all rights reserved.
