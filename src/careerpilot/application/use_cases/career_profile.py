from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.application.errors import (
    CareerProfileAlreadyExistsError,
    CareerProfileNotFoundError,
    UserNotFoundError,
)
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import CareerProfileRepository, UserRepository


@dataclass(frozen=True, slots=True)
class SaveCareerProfileCommand:
    user_id: UUID
    headline: str | None = None
    summary: str | None = None
    skills: tuple[str, ...] = ()
    target_titles: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    years_experience: int | None = None


class SaveCareerProfileUseCase:
    """Create or replace the single career profile for a user."""

    def __init__(
        self,
        *,
        users: UserRepository,
        profiles: CareerProfileRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._clock = clock
        self._ids = ids

    async def execute(self, command: SaveCareerProfileCommand) -> CareerProfile:
        if await self._users.get_by_id(command.user_id) is None:
            raise UserNotFoundError(str(command.user_id))
        existing = await self._profiles.get_by_user_id(command.user_id)
        now = self._clock.now()
        if existing is None:
            profile = CareerProfile.new(
                profile_id=self._ids.new_id(),
                user_id=command.user_id,
                now=now,
                headline=command.headline,
                summary=command.summary,
                skills=command.skills,
                target_titles=command.target_titles,
                locations=command.locations,
                remote_policy=command.remote_policy,
                employment_type=command.employment_type,
                years_experience=command.years_experience,
            )
            await self._profiles.add(profile)
            return profile
        updated = CareerProfile.new(
            profile_id=existing.id,
            user_id=existing.user_id,
            now=now,
            created_at=existing.created_at,
            headline=command.headline,
            summary=command.summary,
            skills=command.skills,
            target_titles=command.target_titles,
            locations=command.locations,
            remote_policy=command.remote_policy,
            employment_type=command.employment_type,
            years_experience=command.years_experience,
        )
        await self._profiles.update(updated)
        return updated


class GetCareerProfileUseCase:
    def __init__(self, *, profiles: CareerProfileRepository) -> None:
        self._profiles = profiles

    async def execute(self, user_id: UUID) -> CareerProfile:
        profile = await self._profiles.get_by_user_id(user_id)
        if profile is None:
            raise CareerProfileNotFoundError(str(user_id))
        return profile


class CreateCareerProfileUseCase:
    """Insert-only. Duplicate user_id is rejected."""

    def __init__(
        self,
        *,
        users: UserRepository,
        profiles: CareerProfileRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._users = users
        self._profiles = profiles
        self._clock = clock
        self._ids = ids

    async def execute(self, command: SaveCareerProfileCommand) -> CareerProfile:
        if await self._users.get_by_id(command.user_id) is None:
            raise UserNotFoundError(str(command.user_id))
        existing = await self._profiles.get_by_user_id(command.user_id)
        if existing is not None:
            raise CareerProfileAlreadyExistsError(str(command.user_id))
        profile = CareerProfile.new(
            profile_id=self._ids.new_id(),
            user_id=command.user_id,
            now=self._clock.now(),
            headline=command.headline,
            summary=command.summary,
            skills=command.skills,
            target_titles=command.target_titles,
            locations=command.locations,
            remote_policy=command.remote_policy,
            employment_type=command.employment_type,
            years_experience=command.years_experience,
        )
        await self._profiles.add(profile)
        return profile
