from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from careerpilot.domain.entities.user import User
from careerpilot.domain.errors import InvalidUserError
from careerpilot.domain.value_objects.user_status import UserStatus


def test_user_new_defaults_to_active() -> None:
    user = User.new(user_id=uuid4(), now=datetime(2026, 9, 22, tzinfo=UTC), display_name="  Ada  ")
    assert user.display_name == "Ada"
    assert user.status is UserStatus.ACTIVE
    assert user.created_at == user.updated_at


def test_user_rejects_naive_datetime() -> None:
    with pytest.raises(InvalidUserError):
        User.new(user_id=uuid4(), now=datetime(2026, 9, 22))


def test_user_rejects_overlong_display_name() -> None:
    with pytest.raises(InvalidUserError):
        User.new(user_id=uuid4(), now=datetime(2026, 9, 22, tzinfo=UTC), display_name="x" * 256)


def test_blank_display_name_becomes_none() -> None:
    user = User.new(user_id=uuid4(), now=datetime(2026, 9, 22, tzinfo=UTC), display_name="   ")
    assert user.display_name is None
