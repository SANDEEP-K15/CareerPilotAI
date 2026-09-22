from __future__ import annotations

from enum import StrEnum


class RemotePolicy(StrEnum):
    UNSPECIFIED = "unspecified"
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"
