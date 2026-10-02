from __future__ import annotations

import json
import re

from careerpilot.application.resume_tailoring.contract import ResumeTailoringLlmOutput
from careerpilot.domain.entities.resume_tailoring import ResumeTailoringChange

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def parse_resume_tailoring_output(raw: str) -> ResumeTailoringLlmOutput | None:
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


def _normalize(payload: dict[str, object]) -> ResumeTailoringLlmOutput | None:
    content_raw = payload.get("tailored_content")
    if not isinstance(content_raw, str):
        return None
    content = content_raw.strip()
    if not content:
        return None
    changes = _changes(payload.get("changes"))
    if changes is None:
        return None
    return ResumeTailoringLlmOutput(tailored_content=content_raw, changes=changes)


def _changes(value: object) -> tuple[ResumeTailoringChange, ...] | None:
    if value is None:
        return ()
    if not isinstance(value, list):
        return None
    items: list[ResumeTailoringChange] = []
    for raw in value:
        if not isinstance(raw, dict):
            return None
        section = raw.get("section")
        description = raw.get("description")
        if not isinstance(section, str) or not isinstance(description, str):
            return None
        section_trimmed = " ".join(section.split())
        description_trimmed = " ".join(description.split())
        if not section_trimmed or not description_trimmed:
            return None
        items.append(
            ResumeTailoringChange(section=section_trimmed, description=description_trimmed)
        )
    return tuple(items)
