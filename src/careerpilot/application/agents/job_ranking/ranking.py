from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.use_cases.match_jobs import InvalidMatchQueryError
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.job_match import JobMatch
from careerpilot.domain.matching import DEFAULT_LIMIT, DEFAULT_THRESHOLD, MAX_LIMIT, rank_matches


@dataclass(frozen=True, slots=True)
class RankJobsQuery:
    user_id: UUID
    job_ids: tuple[UUID, ...]
    threshold: int = DEFAULT_THRESHOLD
    limit: int = DEFAULT_LIMIT


def rank_jobs_for_profile(
    profile: CareerProfile,
    jobs: tuple[Job, ...],
    *,
    threshold: int = DEFAULT_THRESHOLD,
    limit: int = DEFAULT_LIMIT,
) -> tuple[tuple[JobMatch, ...], int, int]:
    """Rank jobs with M7 ``rank_matches``. Does not duplicate scoring rules."""
    _validate_rank_query(threshold, limit)
    accepted = rank_matches(profile, jobs, threshold=threshold)
    considered = len(jobs)
    rejected = considered - len(accepted)
    return accepted[:limit], considered, rejected


def _validate_rank_query(threshold: int, limit: int) -> None:
    if not 0 <= threshold <= 100:
        raise InvalidMatchQueryError("threshold must be between 0 and 100.")
    if not 1 <= limit <= MAX_LIMIT:
        raise InvalidMatchQueryError(f"limit must be between 1 and {MAX_LIMIT}.")
