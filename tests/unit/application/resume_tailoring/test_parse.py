from __future__ import annotations

from careerpilot.application.resume_tailoring.parse import parse_resume_tailoring_output


def test_parse_accepts_minimal_json() -> None:
    parsed = parse_resume_tailoring_output(
        '{"tailored_content": "Jane Doe\\nBackend Engineer", "changes": []}'
    )
    assert parsed is not None
    assert "Jane Doe" in parsed.tailored_content
    assert parsed.changes == ()


def test_parse_accepts_change_items() -> None:
    parsed = parse_resume_tailoring_output(
        '{"tailored_content": "Resume body", "changes": ['
        '{"section": "summary", "description": "Highlighted Python"}'
        "]}"
    )
    assert parsed is not None
    assert len(parsed.changes) == 1
    assert parsed.changes[0].section == "summary"


def test_parse_rejects_missing_content() -> None:
    assert parse_resume_tailoring_output('{"tailored_content": "  ", "changes": []}') is None
    assert parse_resume_tailoring_output('{"changes": []}') is None
