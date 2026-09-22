from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4


class FrozenClock:
    def __init__(self, instant: datetime | None = None) -> None:
        self._instant = instant or datetime(2026, 9, 22, 8, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._instant


class FixedIdGenerator:
    def __init__(self, *ids: UUID) -> None:
        self._ids = list(ids) or [uuid4()]
        self._index = 0

    def new_id(self) -> UUID:
        if self._index >= len(self._ids):
            raise AssertionError("FixedIdGenerator exhausted")
        value = self._ids[self._index]
        self._index += 1
        return value
