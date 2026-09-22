from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.errors import InvalidProfileError
from careerpilot.domain.value_objects.remote_policy import RemotePolicy


def test_profile_normalizes_skills_and_drops_duplicates() -> None:
    profile = CareerProfile.new(
        profile_id=uuid4(),
        user_id=uuid4(),
        now=datetime(2026, 9, 22, tzinfo=UTC),
        skills=(" Python ", "python", "SQL"),
        target_titles=("  ML Intern ",),
        locations=("Bengaluru", "bengaluru"),
        remote_policy=RemotePolicy.REMOTE,
    )
    assert profile.skills == ("Python", "SQL")
    assert profile.target_titles == ("ML Intern",)
    assert profile.locations == ("Bengaluru",)


def test_profile_rejects_naive_datetime() -> None:
    with pytest.raises(InvalidProfileError):
        CareerProfile.new(
            profile_id=uuid4(),
            user_id=uuid4(),
            now=datetime(2026, 9, 22),
        )


def test_profile_rejects_invalid_years() -> None:
    with pytest.raises(InvalidProfileError):
        CareerProfile.new(
            profile_id=uuid4(),
            user_id=uuid4(),
            now=datetime(2026, 9, 22, tzinfo=UTC),
            years_experience=99,
        )
