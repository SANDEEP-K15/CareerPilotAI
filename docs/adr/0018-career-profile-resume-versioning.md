# ADR 0018: Career profile is 1:1; resumes are versioned

## Status

Accepted

## Context

Matching (M7) needs user career facts and a resume. Overwriting resume text
would destroy evidence of what was used in earlier searches or applications.

## Decision

- One `CareerProfile` per user (`uq_career_profiles_user_id`). Updates replace
  fields in place and keep the same profile id and `created_at`.
- Each resume write inserts a new row with a per-user monotonic `version`.
  Content is immutable. At most one `is_active` resume per user.
- Profile fields are matching inputs (skills, titles, locations, remote and
  employment preferences, years of experience). No embeddings, salary, or
  vendor-specific keys.
- Resume content is `text/plain` only. Parsing and tailoring are later
  milestones.
- HTTP DTOs map domain entities; SQLAlchemy models stay in infrastructure.

## Consequences

- Historical resume versions are queryable by version number.
- Matching can read the active resume and current profile without AI.
