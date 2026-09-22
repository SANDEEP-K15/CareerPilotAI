from __future__ import annotations

from enum import StrEnum

from careerpilot.domain.entities.job import Job


class IngestOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    REJECTED = "rejected"


class IngestRawJobResult:
    def __init__(
        self,
        outcome: IngestOutcome,
        *,
        job: Job | None = None,
        reason: str | None = None,
    ) -> None:
        self.outcome = outcome
        self.job = job
        self.reason = reason
