from __future__ import annotations

from typing import Protocol
from uuid import UUID


class IdGeneratorPort(Protocol):
    def new_id(self) -> UUID:
        """Return a new unique identifier."""
        ...
