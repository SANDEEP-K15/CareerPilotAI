# Adzuna job source (optional M3 adapter)

Adzuna is the first **validation** `JobSourcePort` adapter. It is not a
CareerPilot dependency and not the guaranteed source of jobs.

Status: **IMPLEMENTED — NOT EXTERNALLY VALIDATED** (no `ADZUNA__APP_ID` /
`ADZUNA__APP_KEY` were present in this environment).

## Feasibility (public docs, 2026-09-22)

| Topic | Finding | Source |
|---|---|---|
| Auth | Query params `app_id` and `app_key` (required) | [Overview](https://developer.adzuna.com/overview) |
| Search URL | `GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}` | Overview + [Search](https://developer.adzuna.com/docs/search) |
| Country | Path segment (`gb` in official examples; other ISO-like codes exist) | Overview |
| Keywords | `what` | Search docs |
| Location | `where` | Search docs |
| Page size | `results_per_page` (examples use 20) | Search docs |
| Pagination | 1-based `{page}` in the path | Search docs |
| Dates | Result field `created` (ISO-8601, example `...Z`) | Search docs |
| Apply/source URL | `redirect_url` (Adzuna redirect, not a separate employer apply URL) | Search docs |
| Description | Snippet only, not full text | Search docs |
| Remote filter | **Not documented** on the search endpoint | Search docs |
| Rate limits | Default 25/min, 250/day, 1000/week, 2500/month | [Terms](https://developer.adzuna.com/docs/terms_of_service) |
| Errors | Non-200 HTTP status; body is a serialized exception | Overview |

Not implemented because they are not on `JobSourcePort`: salary histogram,
categories, version, `what_exclude`, `salary_min`, `full_time`, `permanent`.

## Configuration

```
ADZUNA__APP_ID=
ADZUNA__APP_KEY=
ADZUNA__COUNTRY=gb
ADZUNA__BASE_URL=https://api.adzuna.com/v1/api
ADZUNA__TIMEOUT_SECONDS=15
```

Empty credentials: adapter raises `JobSourceError` `unavailable` and does
not call the network. Composition roots may register `AdzunaJobSource` on
`JobSourceRegistry`; the registry does not load Adzuna by itself.

## Mapping

`RawJob.source` is `SourceKey("adzuna")` as an adapter identity string, not
a domain enum. Canonical `Job` is unchanged.

Country (`ADZUNA__COUNTRY`, default `gb`) selects the Adzuna search
index. It is adapter configuration. Do not add country onto `Job`;
listing `location` is whatever the search result contained. User-level
country/location preference is a later profile/search concern.
