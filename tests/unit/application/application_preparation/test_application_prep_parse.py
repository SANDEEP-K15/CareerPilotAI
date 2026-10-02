from __future__ import annotations

from careerpilot.application.application_preparation.parse import parse_application_prep_output


def test_parse_accepts_minimal_json() -> None:
    parsed = parse_application_prep_output(
        '{"guidance": "Review Python examples.", "talking_points": [], "interview_questions": []}'
    )
    assert parsed is not None
    assert "Python" in parsed.guidance
    assert parsed.talking_points == ()
    assert parsed.interview_questions == ()


def test_parse_accepts_nested_items() -> None:
    parsed = parse_application_prep_output(
        '{"guidance": "Prep", "talking_points": ['
        '{"section": "skills", "point": "Highlight PostgreSQL"}], '
        '"interview_questions": [{"question": "Describe a API?", "focus": "System design"}]}'
    )
    assert parsed is not None
    assert parsed.talking_points[0].section == "skills"
    assert parsed.interview_questions[0].focus == "System design"


def test_parse_rejects_missing_guidance() -> None:
    assert (
        parse_application_prep_output(
            '{"guidance": "  ", "talking_points": [], "interview_questions": []}'
        )
        is None
    )
