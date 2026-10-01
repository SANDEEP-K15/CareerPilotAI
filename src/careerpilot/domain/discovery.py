"""Daily selection over M7 scores. No embeddings, LLMs, or provider fields."""

from __future__ import annotations

from dataclasses import dataclass

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.daily_discovery import DiscoverySelection
from careerpilot.domain.entities.job import Job
from careerpilot.domain.matching import DEFAULT_THRESHOLD, rank_matches
from careerpilot.domain.value_objects.job_status import JobStatus

DAILY_SELECTION_LIMIT = 20


@dataclass(frozen=True, slots=True)
class DailySelection:
    selections: tuple[DiscoverySelection, ...]
    considered: int
    rejected: int


def select_daily_jobs(
    profile: CareerProfile,
    jobs: tuple[Job, ...],
    *,
    threshold: int = DEFAULT_THRESHOLD,
    limit: int = DAILY_SELECTION_LIMIT,
) -> DailySelection:
    """Keep active jobs, rank with M7, and return at most ``limit`` matches.

    Jobs below the threshold are omitted. The result is never padded.
    """
    seen: set[object] = set()
    eligible: list[Job] = []
    for job in jobs:
        if job.status is not JobStatus.ACTIVE or job.id in seen:
            continue
        seen.add(job.id)
        eligible.append(job)
    ranked = rank_matches(profile, tuple(eligible), threshold=threshold)
    chosen = ranked[:limit]
    return DailySelection(
        selections=tuple(DiscoverySelection.from_match(item) for item in chosen),
        considered=len(eligible),
        rejected=len(eligible) - len(ranked),
    )


def explain_discovery(
    *,
    searchable: bool,
    selected: int,
    limit: int,
    considered: int,
    failure_count: int,
) -> str:
    if not searchable:
        return "Profile has no target titles or locations to search."
    if selected > 0 and selected < limit:
        return (
            f"{selected} sufficiently relevant jobs; fewer than {limit} met the threshold."
        )
    if selected > 0:
        return f"{selected} sufficiently relevant jobs."
    if considered == 0 and failure_count > 0:
        return "No jobs ingested; one or more sources failed."
    if considered == 0:
        return "No jobs returned from registered sources."
    return "No jobs met the relevance threshold."
