from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from careerpilot.application.errors import JobAlreadyExistsError
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.clock import ClockPort
from careerpilot.ports.ids import IdGeneratorPort
from careerpilot.ports.repositories import JobRepository


@dataclass(frozen=True, slots=True)
class PersistJobCommand:
    source: str
    external_id: str
    title: str
    company_name: str
    source_url: str | None = None
    application_url: str | None = None
    location: str | None = None
    remote_policy: RemotePolicy = RemotePolicy.UNSPECIFIED
    employment_type: EmploymentType = EmploymentType.UNSPECIFIED
    description: str | None = None
    posted_at: datetime | None = None
    extra: Mapping[str, object] = field(default_factory=dict)
    status: JobStatus = JobStatus.ACTIVE


class PersistJobUseCase:
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

    async def execute(self, command: PersistJobCommand) -> Job:
        source = SourceKey.parse(command.source)
        external_id = " ".join(command.external_id.split())
        existing = await self._jobs.get_by_source_identity(source, external_id)
        if existing is not None:
            raise JobAlreadyExistsError(source.value, existing.external_id)

        job = Job.new(
            job_id=self._ids.new_id(),
            source=source,
            external_id=external_id,
            title=command.title,
            company_name=command.company_name,
            discovered_at=self._clock.now(),
            source_url=command.source_url,
            application_url=command.application_url,
            location=command.location,
            remote_policy=command.remote_policy,
            employment_type=command.employment_type,
            description=command.description,
            posted_at=command.posted_at,
            extra=command.extra,
            status=command.status,
        )
        await self._jobs.add(job)
        return job
