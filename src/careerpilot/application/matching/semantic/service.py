from __future__ import annotations

from careerpilot.application.llm.execution import InvokeLlmUseCase, LlmInvocation
from careerpilot.application.matching.semantic.parse import parse_semantic_llm_output
from careerpilot.application.matching.semantic.prompt import build_semantic_match_messages
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.job_match import JobMatch
from careerpilot.domain.entities.semantic_match import AugmentedJobMatch, SemanticAnalysis
from careerpilot.domain.hybrid_matching import combine_match_scores


class SemanticMatchingService:
    """LLM semantic analysis for one profile/job pair with deterministic fallback."""

    def __init__(self, *, llm: InvokeLlmUseCase) -> None:
        self._llm = llm

    async def augment(
        self,
        *,
        profile: CareerProfile,
        job: Job,
        deterministic: JobMatch,
        correlation_id: str | None = None,
    ) -> AugmentedJobMatch:
        if not deterministic.passed_filters:
            return AugmentedJobMatch(
                deterministic=deterministic,
                combined_score=deterministic.score,
                semantic=None,
                semantic_applied=False,
            )
        messages = build_semantic_match_messages(profile, job, deterministic)
        result = await self._llm.execute(
            LlmInvocation(
                messages=messages,
                correlation_id=correlation_id,
                user_id=str(profile.user_id),
                task="semantic_job_match",
                metadata={"job_id": str(job.id)},
            )
        )
        if not result.succeeded or result.response is None:
            return _fallback(deterministic)
        parsed = parse_semantic_llm_output(result.response.content)
        if parsed is None:
            return _fallback(deterministic)
        semantic = SemanticAnalysis(
            alignment_score=parsed.alignment_score,
            summary=parsed.summary,
            concerns=parsed.concerns,
        )
        combined = combine_match_scores(
            deterministic=deterministic.score,
            semantic_alignment=semantic.alignment_score,
        )
        return AugmentedJobMatch(
            deterministic=deterministic,
            combined_score=combined,
            semantic=semantic,
            semantic_applied=True,
        )


def _fallback(deterministic: JobMatch) -> AugmentedJobMatch:
    return AugmentedJobMatch(
        deterministic=deterministic,
        combined_score=deterministic.score,
        semantic=None,
        semantic_applied=False,
    )
