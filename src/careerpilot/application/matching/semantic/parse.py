from __future__ import annotations

import json
import re

from careerpilot.application.matching.semantic.contract import SemanticLlmOutput

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def parse_semantic_llm_output(raw: str) -> SemanticLlmOutput | None:
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


def _normalize(payload: dict[str, object]) -> SemanticLlmOutput | None:
    score_raw = payload.get("alignment_score")
    if isinstance(score_raw, bool) or not isinstance(score_raw, int):
        return None
    if not 0 <= score_raw <= 100:
        return None
    summary_raw = payload.get("summary")
    if not isinstance(summary_raw, str):
        return None
    summary = " ".join(summary_raw.split())
    if not summary:
        return None
    concerns = _concerns(payload.get("concerns"))
    if concerns is None:
        return None
    return SemanticLlmOutput(
        alignment_score=score_raw,
        summary=summary,
        concerns=concerns,
    )


def _concerns(value: object) -> tuple[str, ...] | None:
    if value is None:
        return ()
    if not isinstance(value, list):
        return None
    items: list[str] = []
    for raw in value:
        if not isinstance(raw, str):
            return None
        trimmed = " ".join(raw.split())
        if trimmed:
            items.append(trimmed)
    return tuple(items)
