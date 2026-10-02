"""Combine M7 deterministic scores with optional LLM semantic alignment."""

from __future__ import annotations

from careerpilot.domain.entities.semantic_match import AugmentedJobMatch

DETERMINISTIC_WEIGHT = 70
SEMANTIC_WEIGHT = 30


def combine_match_scores(*, deterministic: int, semantic_alignment: int | None) -> int:
    """Blend scores when semantic alignment is available; otherwise keep M7 score."""
    if semantic_alignment is None:
        return max(0, min(100, deterministic))
    bounded_det = max(0, min(100, deterministic))
    bounded_sem = max(0, min(100, semantic_alignment))
    return (bounded_det * DETERMINISTIC_WEIGHT + bounded_sem * SEMANTIC_WEIGHT) // 100


def rank_augmented_matches(
    matches: tuple[AugmentedJobMatch, ...],
    *,
    threshold: int,
) -> tuple[AugmentedJobMatch, ...]:
    accepted = [
        item
        for item in matches
        if item.deterministic.passed_filters and item.combined_score >= threshold
    ]
    accepted.sort(
        key=lambda item: (
            -item.combined_score,
            -item.deterministic.score,
            str(item.deterministic.job_id),
        )
    )
    return tuple(accepted)
