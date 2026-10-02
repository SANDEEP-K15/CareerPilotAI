from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.errors import CareerProfileNotFoundError
from careerpilot.application.matching.semantic.service import SemanticMatchingService
from careerpilot.application.use_cases.match_jobs import InvalidMatchQueryError
from careerpilot.domain.entities.semantic_match import SemanticMatchReport
from careerpilot.domain.hybrid_matching import rank_augmented_matches
from careerpilot.domain.matching import DEFAULT_LIMIT, DEFAULT_THRESHOLD, MAX_LIMIT, match_job
from careerpilot.ports.repositories import CareerProfileRepository, JobRepository


@dataclass(frozen=True, slots=True)
class SemanticMatchJobsCommand:
    user_id: UUID
    threshold: int = DEFAULT_THRESHOLD
    limit: int = DEFAULT_LIMIT


class SemanticMatchJobsUseCase:
    """Score jobs with M7 filters plus optional LLM semantic augmentation."""

    def __init__(
        self,
        *,
        profiles: CareerProfileRepository,
        jobs: JobRepository,
        semantic: SemanticMatchingService,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs
        self._semantic = semantic

    async def execute(self, command: SemanticMatchJobsCommand) -> SemanticMatchReport:
        if not 0 <= command.threshold <= 100:
            raise InvalidMatchQueryError("threshold must be between 0 and 100.")
        if not 1 <= command.limit <= MAX_LIMIT:
            raise InvalidMatchQueryError(f"limit must be between 1 and {MAX_LIMIT}.")
        profile = await self._profiles.get_by_user_id(command.user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(command.user_id))
        catalog = await self._jobs.list_active()
        augmented = []
        applied = 0
        fallback = 0
        for job in catalog:
            deterministic = match_job(profile, job)
            item = await self._semantic.augment(
                profile=profile,
                job=job,
                deterministic=deterministic,
                correlation_id=str(command.user_id),
            )
            if item.semantic_applied:
                applied += 1
            elif deterministic.passed_filters:
                fallback += 1
            augmented.append(item)
        ranked = rank_augmented_matches(tuple(augmented), threshold=command.threshold)
        rejected = len(catalog) - len(ranked)
        return SemanticMatchReport(
            user_id=command.user_id,
            profile_id=profile.id,
            threshold=command.threshold,
            considered=len(catalog),
            rejected=rejected,
            semantic_applied_count=applied,
            semantic_fallback_count=fallback,
            matches=ranked[: command.limit],
        )
