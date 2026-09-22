from __future__ import annotations

from uuid import UUID, uuid4


class Uuid4Generator:
    def new_id(self) -> UUID:
        return uuid4()
