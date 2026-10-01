from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DimensionScore:
    name: str
    score: int
    weight: int


@dataclass(frozen=True, slots=True)
class JobMatch:
    """Deterministic match of one persisted Job against one CareerProfile."""

    job_id: UUID
    score: int
    passed_filters: bool
    hard_filter: str | None
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    reasons: tuple[str, ...]
    concerns: tuple[str, ...]
    dimensions: tuple[DimensionScore, ...]


@dataclass(frozen=True, slots=True)
class MatchReport:
    user_id: UUID
    profile_id: UUID
    threshold: int
    considered: int
    rejected: int
    matches: tuple[JobMatch, ...]
