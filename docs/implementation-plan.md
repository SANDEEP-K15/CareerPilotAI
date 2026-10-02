# Implementation plan

Status: **M15 complete** after verification in this repository. Do not start
M16 without explicit approval.

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
| M1 | Core domain, configuration, PostgreSQL/Alembic | Complete |
| M2 | JobSourcePort, registry, provider errors | Complete |
| M3 | First JobSource adapter (Adzuna, validation only) | Complete |
| M4 | Normalization and deterministic deduplication | Complete |
| M5 | Job search API | Complete |
| M6 | Career profile and resume foundation | Complete |
| M7 | Deterministic matching engine | Complete |
| M8 | Daily job discovery Temporal workflow | Complete |
| M9 | Agent framework | Complete |
| M10 | Job Search Agent | Complete |
| M11 | Job Ranking Agent | Complete |
| M12 | Executive, Planner, Task Router | Complete |
| M13 | LLM provider abstraction | Complete |
| M14 | AI semantic matching | Complete |
| M15 | Hermes integration (HTTP client only) | Complete |
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

## M1 scope (complete)

- Domain: `User`, canonical `Job`, `SourceKey`, employment/remote/status VOs
- Ports: `ClockPort`, `IdGeneratorPort`, `UserRepository`, `JobRepository`
- PostgreSQL models mapped behind those ports
- Alembic revision `m1_001_users_jobs` (`users`, `jobs`)
- Settings with production secret validation
- Unit tests plus optional Postgres integration tests

## M2 scope (complete)

- `JobSourcePort`, `JobSearchQuery`, `RawJob`, `JobSearchPage`
- Normalized `JobSourceError` plus `normalize_job_source_failure`
- `JobSourceRegistry` with duplicate/unknown source errors
- `SearchRegisteredSourcesUseCase` isolates per-source failures
- In-memory fake source for unit/contract tests
- Canonical `Job` unchanged; no HTTP providers

## M3 scope (complete)

- Optional Adzuna `JobSourcePort` adapter in infrastructure only
- Maps documented search JSON to `RawJob`
- Normalizes HTTP/timeout/malformed errors to `JobSourceError`
- Credentials via `ADZUNA__*` environment variables; missing keys do not boot-fail
- Mocked HTTP unit tests; **no live API validation** without credentials

## Explicitly out of M3

Other providers, search HTTP API, matching, agents, Temporal, Hermes, LLM,
resumes, applications, browser automation.

## M4 scope (complete)

- Provider-neutral `job_from_raw` (`RawJob` → canonical `Job`)
- `IngestRawJobUseCase`: created / unchanged / updated / rejected
- `JobRepository.update` (in-memory fake and SQLAlchemy)
- Identity dedupe: unique `(source, external_id)`
- `content_hash` as change detector, not a merge key across sources
- URLs canonicalized; timestamps stored as UTC
- Opaque `extra` only; no vendor fields on `Job`
- Adzuna country remains adapter config (`ADZUNA__COUNTRY`, default `gb`).
  It is not added to the Job domain model.

## Explicitly out of M4

Search HTTP API, matching, ranking, daily recommendations, user profile,
agents, Temporal, LLM, Hermes, resumes, applications, browser automation,
additional real providers.

## M5 scope (complete)

- FastAPI `POST /api/v1/jobs/search`
- Request/response schemas (canonical Job DTO, not RawJob/ORM)
- `SearchAndIngestJobsUseCase` over the registry + M4 ingest
- Explicit `sources` selection; unknown source → API error
- Partial provider failure does not drop other sources
- Pagination from `JobSearchQuery`
- `X-Request-ID` echo/generate only (no observability platform)
- Tests against `InMemoryJobSource`; Adzuna is not called

## Explicitly out of M5

User profiles, resume processing, matching, ranking, daily recommendations,
AI agents, Temporal, LLM, Hermes, browser automation, applications,
additional job providers.

## M6 scope (complete)

- `CareerProfile` domain entity (skills, target titles, locations, remote,
  employment type, years of experience)
- Versioned `Resume` rows; new content never overwrites history
- Repository ports + in-memory and SQLAlchemy adapters
- Alembic `m6_002_profiles_resumes`
- Use cases: save/get profile, add/list/get resume versions
- HTTP DTOs under `/api/v1/users/{id}/profile` and `/resumes`
- No matching, embeddings, LLM parsing, or agents

## Explicitly out of M6

Matching, ranking, embeddings, vector DB, LLM, AI resume parsing, agents,
Temporal, daily recommendations, Hermes, browser automation, applications,
additional job providers.

## M7 scope (complete)

- Deterministic `match_job` / `rank_matches` over persisted Job + CareerProfile
- Hard filters: inactive, remote, employment, location (when specified)
- Integer weighted score with explanations (matched/missing skills)
- `MatchJobsUseCase` reads `list_active`; does not call providers
- `GET /api/v1/users/{user_id}/matches`
- Threshold default 40; do not pad weak results
- M5 job search unchanged

## Explicitly out of M7

LLM, embeddings, vector DB, ranking agents, Temporal, daily recommendations,
Hermes, resume parsing, browser automation, additional providers.

## M8 scope (complete)

- `DailyJobDiscoveryWorkflow` with activities for profile, search/ingest,
  deterministic match, and persist
- `DiscoverDailyJobsUseCase` reuses M4 ingest and M7 `rank_matches`
- Hard filters and the relevance threshold stay in the matcher
- At most 20 selections; no padding
- `daily_discoveries` row keyed by user and UTC day; repeat runs return it
- Provider failures are recorded and do not abort other sources
- M5 search and M7 match HTTP behavior unchanged

## Explicitly out of M8

LLM, embeddings, agents, Hermes, resume tailoring, applications, browser
automation, notifications, additional providers.

## M9 scope (complete)

- `AgentPort`, `AgentInput`, `AgentOutput`, `AgentContext`
- `AgentKey` identifier and `AgentRegistry`
- `ExecuteAgentTaskUseCase` with structured `AgentRunResult`
- Application errors for duplicate/unknown agents and task validation
- Unit tests with stub agents; no LLM or concrete job agents

## Explicitly out of M9

LLM providers, OpenRouter/Anthropic/OpenAI, JobSearchAgent, RankingAgent,
planner/executive agents, Hermes, resume generation, application automation,
embeddings, vector DB, new Temporal workflows.

## M10 scope (complete)

- `JobSearchAgent` (`job_search`) on `AgentPort`
- Parses structured agent input into `SearchJobsCommand`
- Uses `SearchAndIngestJobsUseCase` and existing provider registry
- Returns ingested job snapshots and normalized source failures
- `build_job_search_agent` composition helper for tests/worker wiring
- M5 HTTP search and M4 ingest behavior unchanged

## Explicitly out of M10

LLM providers, ranking AI, planner/executive agents, Hermes, resume
generation, application automation, embeddings, vector DB, new providers.

## M11 scope (complete)

- `JobRankingAgent` (`job_ranking`) on `AgentPort`
- Loads career profile by `AgentContext.user_id`
- Ranks supplied `job_ids` via M7 `rank_matches` (no duplicated scoring)
- Structured rankings with scores, reasons, and concerns
- Deterministic ordering; safe handling of invalid queries
- M5–M10 behavior unchanged

## Explicitly out of M11

LLM/embedding ranking, planner/executive agents, Hermes, resume tailoring,
application automation, new providers.

## M12 scope (complete)

- `TaskPlannerPort`, `UserTaskRequest`, `ExecutionPlan`, and `PlannedStep`
- `DeterministicTaskPlanner` for direct agent intents and `search_and_rank`
- `TaskRouter` builds `AgentTask` values from planned steps
- `Executive` executes plans via `ExecuteAgentTaskUseCase`
- Structured `OrchestrationResult` with per-step agent outcomes
- Unit tests with stub agents and explicit multi-step plans
- M5–M11 behavior unchanged

## Explicitly out of M12

LLM providers, Hermes, resume tailoring, application automation, browser
automation, embeddings, new job providers, new HTTP APIs.

## M13 scope (complete)

- `LlmPort`, `LlmRequest`, `LlmResponse`, `LlmUsage`, normalized `LlmError`
- `LlmProviderKey`, `LlmModelId`, and `LlmProviderRegistry`
- `LlmSettings` (`LLM__PROVIDER`, `LLM__API_KEY`, `LLM__DEFAULT_MODEL`)
- `InvokeLlmUseCase` with structured `LlmCompletionResult`
- `CostManagerPort` and provider-reported cost metadata only
- In-memory fake provider and unit/contract tests
- M0–M12 behavior unchanged

## Explicitly out of M13

OpenRouter/Anthropic/OpenAI adapters, real HTTP calls, AI matching, production
agent prompts, resume generation, LLM planner/executive behavior, Hermes, new
job providers, embeddings/vector DB.

## M14 scope (complete)

- `SemanticMatchingService` via M13 `InvokeLlmUseCase`
- Structured JSON LLM contract and parser
- Prompt construction from `CareerProfile`, `Job`, and M7 baseline
- `combine_match_scores` / `rank_augmented_matches` hybrid ranking
- `SemanticMatchJobsUseCase` with LLM failure fallback
- Unit tests with `FakeLlmProvider`; M7 `match_job` unchanged

## Explicitly out of M14

Vendor SDKs, real API credentials, embeddings/vector DB, resume tailoring,
Executive/Planner LLM wiring, Hermes, applications, browser automation, new
job providers, changes to M7 HTTP matching.

## M15 scope (complete)

- `POST /api/v1/client/tasks` with Bearer auth (`CLIENT__API_TOKEN`)
- Request/response DTOs, `X-Request-ID` / `correlation_id`
- `SubmitClientTaskUseCase` → M12 `Executive` with timeout handling
- Structured HTTP errors (401, 503, 504) and orchestration failure bodies
- `CareerPilotApiClient` for Hermes-side HTTP (infrastructure only)
- Unit/API tests; M5–M14 behavior unchanged

## Explicitly out of M15

Telegram-specific logic, LLM provider changes, new job providers, browser
automation, application submission, resume tailoring, duplicate orchestration,
Executive LLM behavior, M16+ features.

## First production slice

M1–M8. Agents become the primary orchestrator only after the deterministic
job pipeline works.

## Operating mode

PLAN → IMPLEMENT → TEST → VERIFY → DOCUMENT → COMMIT → REPORT.

Stop after each milestone and wait for approval.
