from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.errors import InvalidResumeError


def test_resume_requires_content_and_version() -> None:
    with pytest.raises(InvalidResumeError):
        Resume.new(
            resume_id=uuid4(),
            user_id=uuid4(),
            version=1,
            content="   ",
            created_at=datetime(2026, 9, 22, tzinfo=UTC),
        )
    with pytest.raises(InvalidResumeError):
        Resume.new(
            resume_id=uuid4(),
            user_id=uuid4(),
            version=0,
            content="Experience",
            created_at=datetime(2026, 9, 22, tzinfo=UTC),
        )


def test_resume_preserves_body_text() -> None:
    resume = Resume.new(
        resume_id=uuid4(),
        user_id=uuid4(),
        version=1,
        content="Ada\nML intern",
        created_at=datetime(2026, 9, 22, tzinfo=UTC),
        label="  v1  ",
    )
    assert resume.content == "Ada\nML intern"
    assert resume.label == "v1"
    assert resume.version == 1
    assert resume.is_active is False
