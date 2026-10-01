from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.errors import ApplicationError, CareerProfileNotFoundError
from careerpilot.domain.entities.job_match import MatchReport
from careerpilot.domain.matching import DEFAULT_LIMIT, DEFAULT_THRESHOLD, MAX_LIMIT, rank_matches
from careerpilot.ports.repositories import CareerProfileRepository, JobRepository


class InvalidMatchQueryError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_match_query")


@dataclass(frozen=True, slots=True)
class MatchJobsCommand:
    user_id: UUID
    threshold: int = DEFAULT_THRESHOLD
    limit: int = DEFAULT_LIMIT


class MatchJobsUseCase:
    """Score persisted jobs against a user's career profile. Does not search providers."""

    def __init__(
        self,
        *,
        profiles: CareerProfileRepository,
        jobs: JobRepository,
    ) -> None:
        self._profiles = profiles
        self._jobs = jobs

    async def execute(self, command: MatchJobsCommand) -> MatchReport:
        if not 0 <= command.threshold <= 100:
            raise InvalidMatchQueryError("threshold must be between 0 and 100.")
        if not 1 <= command.limit <= MAX_LIMIT:
            raise InvalidMatchQueryError(f"limit must be between 1 and {MAX_LIMIT}.")
        profile = await self._profiles.get_by_user_id(command.user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(command.user_id))
        catalog = await self._jobs.list_active()
        accepted = rank_matches(profile, catalog, threshold=command.threshold)
        considered = len(catalog)
        rejected = considered - len(accepted)
        return MatchReport(
            user_id=command.user_id,
            profile_id=profile.id,
            threshold=command.threshold,
            considered=considered,
            rejected=rejected,
            matches=accepted[: command.limit],
        )
