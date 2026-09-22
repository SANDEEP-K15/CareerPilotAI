# Job Search HTTP API (M5)

Versioned FastAPI delivery. The HTTP layer does not call job providers.
It invokes application use cases only.

## Endpoint

`POST /api/v1/jobs/search`

Header: `X-Request-ID` is echoed when sent, otherwise generated.

## Request

```json
{
  "keywords": ["intern"],
  "location": null,
  "remote_only": null,
  "page": 1,
  "page_size": 20,
  "sources": ["example_board"]
}
```

Fields match `JobSearchQuery` plus optional `sources`. Unknown fields are
rejected. Do not send provider-specific keys (`country`, `app_id`, …).

- `sources` omitted: every **registered** source (the registry may be empty).
- `sources` present: those keys only; empty list is invalid.
- Unknown source: `404` `unknown_job_source`.

No source is registered by default. Adzuna is never implied.

## Success response (`200`)

Canonical `Job` items (not `RawJob`, not ORM rows). Per-source pagination
and per-source errors are included so one failure does not drop others.

```json
{
  "items": [
    {
      "id": "…",
      "source": "example_board",
      "external_id": "ext-1",
      "title": "ML Intern",
      "company_name": "Acme",
      "source_url": "https://example.com/jobs/ext-1",
      "application_url": null,
      "location": null,
      "remote_policy": "unspecified",
      "employment_type": "unspecified",
      "description": null,
      "posted_at": null,
      "discovered_at": "2026-09-22T08:00:00Z",
      "content_hash": "…",
      "status": "active"
    }
  ],
  "page": 1,
  "page_size": 20,
  "has_more": false,
  "sources": [
    {
      "source": "example_board",
      "page": 1,
      "page_size": 20,
      "returned": 1,
      "has_more": false
    }
  ],
  "errors": [],
  "request_id": "…"
}
```

`extra` / provider metadata is not part of the HTTP contract.

## Errors

| Status | `error.code` | When |
|---|---|---|
| 422 | `invalid_job_search_query` | Missing keywords and location, bad page |
| 422 | `invalid_request` | Schema / unknown fields |
| 404 | `unknown_job_source` | Source not in the registry |
| 422 | `invalid_job` | Malformed source key |
| 200 + `errors[]` | provider `timeout` / `unavailable` / … | Source failed; other sources still returned |

Bodies use `{ "error": { "code", "message" }, "request_id" }`. No traces.

## Flow

HTTP → `SearchJobsCommand` → `SearchAndIngestJobsUseCase` →
`JobSourceRegistry` / `JobSourcePort` → `RawJob` → `IngestRawJobUseCase` →
`JobRepository` → canonical `Job` DTO.

## Local run

Compose a registry in process (tests inject `InMemoryJobSource`). Example:

```python
from careerpilot.api.app import create_app
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
```

Do not point this API at Adzuna from application or API code.

## Career profile and resumes (M6)

DTOs only. No ORM models, no embeddings, no parsed structured resume trees.

`PUT /api/v1/users/{user_id}/profile` — create or replace the user's single profile  
`GET /api/v1/users/{user_id}/profile`  
`POST /api/v1/users/{user_id}/resumes` — append an immutable version (becomes active)  
`GET /api/v1/users/{user_id}/resumes`  
`GET /api/v1/users/{user_id}/resumes/active`  
`GET /api/v1/users/{user_id}/resumes/{version}`

Profile body: `headline`, `summary`, `skills`, `target_titles`, `locations`,
`remote_policy`, `employment_type`, `years_experience`. Extra fields rejected.

Resume body: `content` (plain text), optional `label`. Previous versions remain.

`404` `user_not_found` / `career_profile_not_found` / `resume_not_found`.
`422` `invalid_profile` / `invalid_resume` / `invalid_request`.

