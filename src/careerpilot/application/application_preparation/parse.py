from __future__ import annotations

import json
import re

from careerpilot.application.application_preparation.contract import ApplicationPrepLlmOutput
from careerpilot.domain.entities.application_prep import (
    ApplicationPrepInterviewQuestion,
    ApplicationPrepTalkingPoint,
)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def parse_application_prep_output(raw: str) -> ApplicationPrepLlmOutput | None:
    """Parse provider text into a normalized contract. Returns None when invalid."""
    trimmed = raw.strip()
    if not trimmed:
        return None
    payload = _load_json_object(trimmed)
    if payload is None:
        return None
    return _normalize(payload)


def _load_json_object(text: str) -> dict[str, object] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_BLOCK.search(text)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _normalize(payload: dict[str, object]) -> ApplicationPrepLlmOutput | None:
    guidance_raw = payload.get("guidance")
    if not isinstance(guidance_raw, str):
        return None
    guidance = guidance_raw.strip()
    if not guidance:
        return None
    talking_points = _talking_points(payload.get("talking_points"))
    if talking_points is None:
        return None
    interview_questions = _interview_questions(payload.get("interview_questions"))
    if interview_questions is None:
        return None
    return ApplicationPrepLlmOutput(
        guidance=guidance_raw,
        talking_points=talking_points,
        interview_questions=interview_questions,
    )


def _talking_points(value: object) -> tuple[ApplicationPrepTalkingPoint, ...] | None:
    if value is None:
        return ()
    if not isinstance(value, list):
        return None
    items: list[ApplicationPrepTalkingPoint] = []
    for raw in value:
        if not isinstance(raw, dict):
            return None
        section = raw.get("section")
        point = raw.get("point")
        if not isinstance(section, str) or not isinstance(point, str):
            return None
        section_trimmed = " ".join(section.split())
        point_trimmed = " ".join(point.split())
        if not section_trimmed or not point_trimmed:
            return None
        items.append(ApplicationPrepTalkingPoint(section=section_trimmed, point=point_trimmed))
    return tuple(items)


def _interview_questions(value: object) -> tuple[ApplicationPrepInterviewQuestion, ...] | None:
    if value is None:
        return ()
    if not isinstance(value, list):
        return None
    items: list[ApplicationPrepInterviewQuestion] = []
    for raw in value:
        if not isinstance(raw, dict):
            return None
        question = raw.get("question")
        focus = raw.get("focus")
        if not isinstance(question, str) or not isinstance(focus, str):
            return None
        question_trimmed = " ".join(question.split())
        focus_trimmed = " ".join(focus.split())
        if not question_trimmed or not focus_trimmed:
            return None
        items.append(
            ApplicationPrepInterviewQuestion(question=question_trimmed, focus=focus_trimmed)
        )
    return tuple(items)
