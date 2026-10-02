"""Structured application preparation output expected from the LLM."""

from __future__ import annotations

from dataclasses import dataclass

from careerpilot.domain.entities.application_prep import (
    ApplicationPrepInterviewQuestion,
    ApplicationPrepTalkingPoint,
)


@dataclass(frozen=True, slots=True)
class ApplicationPrepLlmOutput:
    guidance: str
    talking_points: tuple[ApplicationPrepTalkingPoint, ...]
    interview_questions: tuple[ApplicationPrepInterviewQuestion, ...]
