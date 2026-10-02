from __future__ import annotations

from careerpilot.application.matching.semantic.parse import parse_semantic_llm_output


def test_parse_accepts_minimal_json() -> None:
    parsed = parse_semantic_llm_output(
        '{"alignment_score": 72, "summary": "Strong overlap", "concerns": []}'
    )
    assert parsed is not None
    assert parsed.alignment_score == 72
    assert parsed.summary == "Strong overlap"
    assert parsed.concerns == ()


def test_parse_extracts_json_from_surrounding_text() -> None:
    parsed = parse_semantic_llm_output(
        'Here is the result:\n{"alignment_score": 10, "summary": "Weak fit", "concerns": ["gap"]}\n'
    )
    assert parsed is not None
    assert parsed.concerns == ("gap",)


def test_parse_rejects_invalid_score() -> None:
    assert (
        parse_semantic_llm_output('{"alignment_score": 101, "summary": "x", "concerns": []}')
        is None
    )
    assert (
        parse_semantic_llm_output('{"alignment_score": "high", "summary": "x", "concerns": []}')
        is None
    )
