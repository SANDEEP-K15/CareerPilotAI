# CareerPilot AI

CareerPilot AI is an AI-powered career intelligence and job automation
platform. It discovers relevant jobs, evaluates fit against a user's career
profile, and eventually helps prepare applications while keeping human
approval as a hard boundary for consequential actions.

This repository is the product. Hermes, Telegram, web, and CLI clients are
interfaces. They must not contain CareerPilot business logic.

## Current milestone

**M19 — Browser automation abstraction.**

Provider-neutral `BrowserAutomationPort` / `BrowserSessionPort` define
navigation, page inspection, form interaction, and screenshot artifacts with
structured errors. The in-memory fake supports contract tests; no real browser
or application submission (ADR 0031). M5–M18 unchanged.

Not yet implemented: real browser drivers, application workflow (M20), or submission execution.

## What works today

| Area | Status |
|---|---|
| Domain, use cases, ports, Postgres repositories, Alembic migrations | Implemented and tested (unit, contract, integration) |
| Adzuna job source | Implemented adapter; needs Adzuna credentials to call the live API |
| LLM | Provider-neutral `LlmPort` plus an Anthropic adapter (`infrastructure/llm`), selected with `LLM__PROVIDER=anthropic`. Tested offline through the real SDK client with an in-memory transport; no live call is made in the test suite |
| Semantic matching, resume tailoring, application preparation | Use cases implemented against `LlmPort`; exercised with fakes in tests |
| HTTP API | `create_app()` takes its use cases as arguments; there is no composition root or ASGI entry point yet, so the API is exercised through tests only |
| Ranking quality | Not yet evaluated (see `evaluation/`) |

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
  application/       Use cases, job-source registry, agent framework
  ports/             Clock, IDs, repositories (JobSourcePort in M2)
  infrastructure/    Postgres adapters; optional Adzuna JobSourcePort
  config/            pydantic-settings
  api/               FastAPI delivery (`/api/v1`)
  worker/            Temporal worker (`python -m careerpilot.worker`)
database/            Alembic migrations
tests/               Unit, integration, and contract tests
```

## Documentation

- [Implementation plan](docs/implementation-plan.md)
- [Architecture](docs/architecture/overview.md)
- [ADRs](docs/adr/)
- [HTTP API](docs/api.md)
- [Adzuna provider](docs/providers/adzuna.md)
- [Database](database/README.md)

## License

Proprietary — all rights reserved.
