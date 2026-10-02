from __future__ import annotations

from uuid import uuid4

from careerpilot.domain.entities.job_match import JobMatch
from careerpilot.domain.entities.semantic_match import AugmentedJobMatch
from careerpilot.domain.hybrid_matching import combine_match_scores, rank_augmented_matches


def _deterministic(*, score: int, passed: bool = True) -> JobMatch:
    return JobMatch(
        job_id=uuid4(),
        score=score,
        passed_filters=passed,
        hard_filter=None if passed else "remote_policy",
        matched_skills=(),
        missing_skills=(),
        reasons=(),
        concerns=(),
        dimensions=(),
    )


def test_combine_match_scores_falls_back_to_deterministic() -> None:
    assert combine_match_scores(deterministic=55, semantic_alignment=None) == 55


def test_combine_match_scores_blends_with_fixed_weights() -> None:
    assert combine_match_scores(deterministic=50, semantic_alignment=100) == 65
    assert combine_match_scores(deterministic=80, semantic_alignment=0) == 56


def test_rank_augmented_matches_uses_combined_score() -> None:
    weaker = AugmentedJobMatch(
        deterministic=_deterministic(score=80),
        combined_score=80,
        semantic=None,
        semantic_applied=False,
    )
    stronger = AugmentedJobMatch(
        deterministic=_deterministic(score=50),
        combined_score=65,
        semantic=None,
        semantic_applied=True,
    )
    ranked = rank_augmented_matches((weaker, stronger), threshold=40)
    assert [item.combined_score for item in ranked] == [80, 65]
