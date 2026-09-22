from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from careerpilot.domain.errors import InvalidProfileError
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy

_MAX_HEADLINE = 200
_MAX_SUMMARY = 4000
_MAX_SKILL = 64
_MAX_SKILLS = 50
_MAX_TITLE = 200
_MAX_TITLES = 20
_MAX_LOCATION = 255
_MAX_LOCATIONS = 20
_MAX_YEARS = 60


@dataclass(slots=True)
class CareerProfile:
    """User-owned career facts for later deterministic matching. Not a job listing."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    headline: str | None = None
    summary: str | None = None
    skills: tuple[str, ...] = ()
    target_titles: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    years_experience: int | None = None

    @classmethod
    def new(
        cls,
        *,
        profile_id: UUID,
        user_id: UUID,
        now: datetime,
        headline: str | None = None,
        summary: str | None = None,
        skills: Sequence[str] = (),
        target_titles: Sequence[str] = (),
        locations: Sequence[str] = (),
        remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED,
        employment_type: EmploymentType = EmploymentType.UNSPECIFIED,
        years_experience: int | None = None,
        created_at: datetime | None = None,
    ) -> CareerProfile:
        _require_aware(now, field="now")
        created = created_at if created_at is not None else now
        _require_aware(created, field="created_at")
        return cls(
            id=profile_id,
            user_id=user_id,
            created_at=created,
            updated_at=now,
            headline=_optional_text(headline, field="headline", max_len=_MAX_HEADLINE),
            summary=_optional_text(summary, field="summary", max_len=_MAX_SUMMARY),
            skills=_unique_terms(skills, field="skills", max_len=_MAX_SKILL, max_items=_MAX_SKILLS),
            target_titles=_unique_terms(
                target_titles, field="target_titles", max_len=_MAX_TITLE, max_items=_MAX_TITLES
            ),
            locations=_unique_terms(
                locations, field="locations", max_len=_MAX_LOCATION, max_items=_MAX_LOCATIONS
            ),
            remote_policy=remote_policy,
            employment_type=employment_type,
            years_experience=_years(years_experience),
        )


def _optional_text(value: str | None, *, field: str, max_len: int) -> str | None:
    if value is None:
        return None
    trimmed = " ".join(value.split())
    if not trimmed:
        return None
    if len(trimmed) > max_len:
        raise InvalidProfileError(f"{field} must be at most {max_len} characters.")
    return trimmed


def _unique_terms(
    values: Sequence[str], *, field: str, max_len: int, max_items: int
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        trimmed = " ".join(raw.split())
        if not trimmed:
            continue
        if len(trimmed) > max_len:
            raise InvalidProfileError(f"each {field} item must be at most {max_len} characters.")
        key = trimmed.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(trimmed)
    if len(result) > max_items:
        raise InvalidProfileError(f"{field} must contain at most {max_items} items.")
    return tuple(result)


def _years(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 0 or value > _MAX_YEARS:
        raise InvalidProfileError(f"years_experience must be between 0 and {_MAX_YEARS}.")
    return value


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidProfileError(f"{field} must be timezone-aware UTC datetime.")
