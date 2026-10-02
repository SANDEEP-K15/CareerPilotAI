from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.domain.errors import InvalidResumeError

_MAX_CONTENT = 200_000
_MAX_CHANGES = 50
_MAX_SECTION = 100
_MAX_CHANGE_DESC = 500


@dataclass(frozen=True, slots=True)
class ResumeTailoringChange:
    section: str
    description: str


@dataclass(frozen=True, slots=True)
class ResumeTailoringResult:
    """Tailored resume output. Does not replace stored resume versions."""

    user_id: UUID
    job_id: UUID
    source_resume_id: UUID
    source_resume_version: int
    tailored_content: str
    changes: tuple[ResumeTailoringChange, ...]
    llm_provider: str
    llm_model: str

    @classmethod
    def new(
        cls,
        *,
        user_id: UUID,
        job_id: UUID,
        source_resume_id: UUID,
        source_resume_version: int,
        tailored_content: str,
        changes: tuple[ResumeTailoringChange, ...],
        llm_provider: str,
        llm_model: str,
    ) -> ResumeTailoringResult:
        body = tailored_content.strip()
        if not body:
            raise InvalidResumeError("tailored_content is required.")
        if len(tailored_content) > _MAX_CONTENT:
            raise InvalidResumeError(f"tailored_content must be at most {_MAX_CONTENT} characters.")
        if len(changes) > _MAX_CHANGES:
            raise InvalidResumeError(f"changes must contain at most {_MAX_CHANGES} items.")
        normalized = tuple(_normalize_change(item) for item in changes)
        provider = llm_provider.strip()
        model = llm_model.strip()
        if not provider or not model:
            raise InvalidResumeError("llm_provider and llm_model are required.")
        return cls(
            user_id=user_id,
            job_id=job_id,
            source_resume_id=source_resume_id,
            source_resume_version=source_resume_version,
            tailored_content=tailored_content,
            changes=normalized,
            llm_provider=provider,
            llm_model=model,
        )


def _normalize_change(item: ResumeTailoringChange) -> ResumeTailoringChange:
    section = " ".join(item.section.split())
    description = " ".join(item.description.split())
    if not section or not description:
        raise InvalidResumeError("change section and description are required.")
    if len(section) > _MAX_SECTION:
        raise InvalidResumeError(f"change section must be at most {_MAX_SECTION} characters.")
    if len(description) > _MAX_CHANGE_DESC:
        raise InvalidResumeError(
            f"change description must be at most {_MAX_CHANGE_DESC} characters."
        )
    return ResumeTailoringChange(section=section, description=description)
