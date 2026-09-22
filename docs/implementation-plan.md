# Implementation plan

Status: **M0 complete** after verification in this repository. Do not start
M1 without explicit approval.

## Product goal

Reliable personalized job discovery for multiple users, with later
application assistance under human approval. CareerPilot is not an Adzuna
wrapper and not a Hermes plugin.

Job providers are interchangeable adapters. Domain, application services,
`JobSourcePort`, and the registry must stay provider-neutral so a new
source can be added without changing domain or application logic.

Adzuna is scheduled only as the **first concrete adapter for validation**
in M3. It must not become a hard dependency, a default assumed to always
be present, or the conceptual primary source of jobs.

## Milestone tracker

| ID | Scope | Status |
|---|---|---|
| M0 | Architecture and repository foundation | Complete |
| M1 | Core domain, configuration, PostgreSQL/Alembic | Not started |
| M2 | JobSourcePort, registry, provider errors | Not started |
| M3 | First JobSource adapter (Adzuna, validation only) | Not started |
| M4 | Normalization and deterministic deduplication | Not started |
| M5 | Job search API | Not started |
| M6 | Career profile and resume foundation | Not started |
| M7 | Deterministic matching engine | Not started |
| M8 | Daily job discovery Temporal workflow | Not started |
| M9 | Agent framework | Not started |
| M10 | Job Search Agent | Not started |
| M11 | Job Ranking Agent | Not started |
| M12 | Executive, Planner, Task Router | Not started |
| M13 | LLM provider abstraction | Not started |
| M14 | AI semantic matching | Not started |
| M15 | Hermes integration (HTTP client only) | Not started |
| M16 | Resume tailoring | Not started |
| M17 | Application preparation | Not started |
| M18 | Approval system | Not started |
| M19 | Browser automation abstraction | Not started |
| M20 | Application workflow | Not started |
| M21 | Evaluation framework | Not started |
| M22 | Production hardening | Not started |

## M0 scope (approved)

- Git repository
- Tooling: uv, Ruff, strict mypy, pytest
- Package skeleton with hexagonal directory boundaries
- Docs: architecture, implementation plan, ADRs
- `.env.example` with no real secrets
- Docker Compose: PostgreSQL only
- CI: lint, typecheck, tests, compose config validation
- `evaluation/` stubs (not implemented)

## Explicitly out of M0

Domain tables, JobSource implementations (including Adzuna), search,
matching, agents, Temporal worker, Hermes, LLM, resumes, applications,
browser automation.

## First production slice

M1–M8. Agents become the primary orchestrator only after the deterministic
job pipeline works.

## Operating mode

PLAN → IMPLEMENT → TEST → VERIFY → DOCUMENT → COMMIT → REPORT.

Stop after each milestone and wait for approval.
