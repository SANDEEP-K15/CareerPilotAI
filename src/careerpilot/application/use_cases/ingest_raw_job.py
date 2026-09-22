from __future__ import annotations

from careerpilot.application.jobs.ingest_types import IngestOutcome, IngestRawJobResult
from careerpilot.application.jobs.normalization import job_from_raw, jobs_are_equivalent
from careerpilot.domain.errors import InvalidJobError
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.job_source import RawJob
from careerpilot.ports.repositories import JobRepository


class IngestRawJobUseCase:
    """Normalize a RawJob and persist it idempotently.

    Identity is (source, external_id). Same identity + equivalent content is a
    no-op. Same identity + different content updates the existing row in place.
    Different sources never collapse into one row.
    """

    def __init__(
        self,
        *,
        jobs: JobRepository,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._jobs = jobs
        self._clock = clock
        self._ids = ids

    async def execute(self, raw: RawJob) -> IngestRawJobResult:
        existing = await self._jobs.get_by_source_identity(
            raw.source, " ".join(raw.external_id.split())
        )
        try:
            if existing is None:
                job = job_from_raw(raw, job_id=self._ids.new_id(), discovered_at=self._clock.now())
            else:
                job = job_from_raw(raw, job_id=existing.id, discovered_at=existing.discovered_at)
                job.status = existing.status
                job.remote_policy = existing.remote_policy
                job.employment_type = existing.employment_type
        except InvalidJobError as exc:
            return IngestRawJobResult(IngestOutcome.REJECTED, reason=exc.message)

        if existing is None:
            await self._jobs.add(job)
            return IngestRawJobResult(IngestOutcome.CREATED, job=job)

        if jobs_are_equivalent(existing, job):
            return IngestRawJobResult(IngestOutcome.UNCHANGED, job=existing)

        await self._jobs.update(job)
        return IngestRawJobResult(IngestOutcome.UPDATED, job=job)
