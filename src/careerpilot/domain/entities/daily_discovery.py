from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from careerpilot.domain.entities.job_match import JobMatch


@dataclass(frozen=True, slots=True)
class DiscoverySelection:
    """Snapshot of one selected job. Stable after the daily run is stored."""

    job_id: UUID
    score: int
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    reasons: tuple[str, ...]
    concerns: tuple[str, ...]

    @classmethod
    def from_match(cls, match: JobMatch) -> DiscoverySelection:
        return cls(
            job_id=match.job_id,
            score=match.score,
            matched_skills=match.matched_skills,
            missing_skills=match.missing_skills,
            reasons=match.reasons,
            concerns=match.concerns,
        )


@dataclass(frozen=True, slots=True)
class DiscoverySourceFailure:
    source: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class DailyDiscovery:
    """One user's discovery result for a UTC calendar day."""

    id: UUID
    user_id: UUID
    profile_id: UUID
    run_on: date
    threshold: int
    limit: int
    considered: int
    rejected: int
    selections: tuple[DiscoverySelection, ...]
    failures: tuple[DiscoverySourceFailure, ...]
    explanation: str
    created_at: datetime
    updated_at: datetime
