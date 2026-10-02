from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.domain.entities.job_match import JobMatch


@dataclass(frozen=True, slots=True)
class SemanticAnalysis:
    """Normalized semantic assessment parsed from LLM output."""

    alignment_score: int
    summary: str
    concerns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AugmentedJobMatch:
    """M7 deterministic match plus optional semantic augmentation."""

    deterministic: JobMatch
    combined_score: int
    semantic: SemanticAnalysis | None
    semantic_applied: bool


@dataclass(frozen=True, slots=True)
class SemanticMatchReport:
    user_id: UUID
    profile_id: UUID
    threshold: int
    considered: int
    rejected: int
    semantic_applied_count: int
    semantic_fallback_count: int
    matches: tuple[AugmentedJobMatch, ...]
