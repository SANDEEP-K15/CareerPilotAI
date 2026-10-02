from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from careerpilot.domain.errors import InvalidApplicationPrepError

_MAX_GUIDANCE = 4_000
_MAX_ITEMS = 30
_MAX_SECTION = 100
_MAX_POINT = 500
_MAX_QUESTION = 500
_MAX_FOCUS = 500


@dataclass(frozen=True, slots=True)
class ApplicationPrepTalkingPoint:
    section: str
    point: str


@dataclass(frozen=True, slots=True)
class ApplicationPrepInterviewQuestion:
    question: str
    focus: str


@dataclass(frozen=True, slots=True)
class ApplicationPrepPackage:
    """Structured interview/application prep for one user and job. Read-only inputs."""

    user_id: UUID
    job_id: UUID
    source_resume_id: UUID
    source_resume_version: int
    guidance: str
    talking_points: tuple[ApplicationPrepTalkingPoint, ...]
    interview_questions: tuple[ApplicationPrepInterviewQuestion, ...]
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
        guidance: str,
        talking_points: tuple[ApplicationPrepTalkingPoint, ...],
        interview_questions: tuple[ApplicationPrepInterviewQuestion, ...],
        llm_provider: str,
        llm_model: str,
    ) -> ApplicationPrepPackage:
        body = guidance.strip()
        if not body:
            raise InvalidApplicationPrepError("guidance is required.")
        if len(guidance) > _MAX_GUIDANCE:
            raise InvalidApplicationPrepError(
                f"guidance must be at most {_MAX_GUIDANCE} characters."
            )
        if len(talking_points) > _MAX_ITEMS:
            raise InvalidApplicationPrepError(
                f"talking_points must contain at most {_MAX_ITEMS} items."
            )
        if len(interview_questions) > _MAX_ITEMS:
            raise InvalidApplicationPrepError(
                f"interview_questions must contain at most {_MAX_ITEMS} items."
            )
        provider = llm_provider.strip()
        model = llm_model.strip()
        if not provider or not model:
            raise InvalidApplicationPrepError("llm_provider and llm_model are required.")
        return cls(
            user_id=user_id,
            job_id=job_id,
            source_resume_id=source_resume_id,
            source_resume_version=source_resume_version,
            guidance=guidance,
            talking_points=tuple(_normalize_point(item) for item in talking_points),
            interview_questions=tuple(_normalize_question(item) for item in interview_questions),
            llm_provider=provider,
            llm_model=model,
        )


def _normalize_point(item: ApplicationPrepTalkingPoint) -> ApplicationPrepTalkingPoint:
    section = " ".join(item.section.split())
    point = " ".join(item.point.split())
    if not section or not point:
        raise InvalidApplicationPrepError("talking point section and point are required.")
    if len(section) > _MAX_SECTION:
        raise InvalidApplicationPrepError(
            f"talking point section must be at most {_MAX_SECTION} characters."
        )
    if len(point) > _MAX_POINT:
        raise InvalidApplicationPrepError(
            f"talking point must be at most {_MAX_POINT} characters."
        )
    return ApplicationPrepTalkingPoint(section=section, point=point)


def _normalize_question(item: ApplicationPrepInterviewQuestion) -> ApplicationPrepInterviewQuestion:
    question = " ".join(item.question.split())
    focus = " ".join(item.focus.split())
    if not question or not focus:
        raise InvalidApplicationPrepError("interview question and focus are required.")
    if len(question) > _MAX_QUESTION:
        raise InvalidApplicationPrepError(
            f"interview question must be at most {_MAX_QUESTION} characters."
        )
    if len(focus) > _MAX_FOCUS:
        raise InvalidApplicationPrepError(
            f"interview question focus must be at most {_MAX_FOCUS} characters."
        )
    return ApplicationPrepInterviewQuestion(question=question, focus=focus)
