from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from careerpilot.domain.errors import InvalidUserError
from careerpilot.domain.value_objects.user_status import UserStatus

_MAX_DISPLAY_NAME = 255


@dataclass(slots=True)
class User:
    """Identity root. Client-specific handles (Hermes, Telegram) are not keys."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    display_name: str | None = None
    status: UserStatus = UserStatus.ACTIVE

    @classmethod
    def new(
        cls,
        *,
        user_id: UUID,
        now: datetime,
        display_name: str | None = None,
    ) -> User:
        _require_aware(now, field="now")
        return cls(
            id=user_id,
            created_at=now,
            updated_at=now,
            display_name=_validate_display_name(display_name),
            status=UserStatus.ACTIVE,
        )


def _validate_display_name(display_name: str | None) -> str | None:
    if display_name is None:
        return None
    trimmed = " ".join(display_name.split())
    if not trimmed:
        return None
    if len(trimmed) > _MAX_DISPLAY_NAME:
        raise InvalidUserError(f"display_name must be at most {_MAX_DISPLAY_NAME} characters.")
    return trimmed


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidUserError(f"{field} must be timezone-aware UTC datetime.")
