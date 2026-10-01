# ADR 0020: Daily job discovery is a Temporal workflow

## Status

Accepted

## Context

Daily discovery needs retries and a stable result if an activity runs twice.
Matching and ingest already exist. The workflow must not reimplement them
or call an LLM.

## Decision

- `DailyJobDiscoveryWorkflow` orchestrates four activities: load an existing
  run, load the career profile, search registered sources through the M4
  ingest path, then rank with M7 and persist.
- Business rules live in `DiscoverDailyJobsUseCase` and `select_daily_jobs`.
- One row per `(user_id, run_on)`. A repeat save returns the stored row.
- Select at most 20 jobs at or above the match threshold. Do not pad.
- Provider failures are stored on the run. They do not drop other sources
  and do not fail the workflow.
- A missing profile fails the workflow and is not retried.
- Workflow id is `daily-job-discovery-{user_id}-{run_on}`.
- No HTTP route, notification, agent, or new job provider.

## Consequences

- M5 search and M7 `MatchJobsUseCase` stay request-scoped and unchanged.
- The worker process is the composition root that registers optional
  adapters which already have credentials.
