from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from careerpilot.domain.errors import InvalidResumeError

_MAX_LABEL = 100
_MAX_CONTENT = 200_000


class ResumeContentType(StrEnum):
    TEXT_PLAIN = "text/plain"


@dataclass(slots=True)
class Resume:
    """Immutable resume version. New content is a new row, never an overwrite."""

    id: UUID
    user_id: UUID
    version: int
    content: str
    created_at: datetime
    label: str | None = None
    content_type: ResumeContentType = ResumeContentType.TEXT_PLAIN
    is_active: bool = False

    @classmethod
    def new(
        cls,
        *,
        resume_id: UUID,
        user_id: UUID,
        version: int,
        content: str,
        created_at: datetime,
        label: str | None = None,
        content_type: ResumeContentType = ResumeContentType.TEXT_PLAIN,
        is_active: bool = False,
    ) -> Resume:
        _require_aware(created_at, field="created_at")
        if version < 1:
            raise InvalidResumeError("version must be >= 1.")
        body = content.strip()
        if not body:
            raise InvalidResumeError("content is required.")
        if len(content) > _MAX_CONTENT:
            raise InvalidResumeError(f"content must be at most {_MAX_CONTENT} characters.")
        if content_type is not ResumeContentType.TEXT_PLAIN:
            raise InvalidResumeError("content_type must be text/plain.")
        return cls(
            id=resume_id,
            user_id=user_id,
            version=version,
            content=content,
            created_at=created_at,
            label=_optional_label(label),
            content_type=content_type,
            is_active=is_active,
        )


def _optional_label(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = " ".join(value.split())
    if not trimmed:
        return None
    if len(trimmed) > _MAX_LABEL:
        raise InvalidResumeError(f"label must be at most {_MAX_LABEL} characters.")
    return trimmed


def _require_aware(value: datetime, *, field: str) -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise InvalidResumeError(f"{field} must be timezone-aware UTC datetime.")
