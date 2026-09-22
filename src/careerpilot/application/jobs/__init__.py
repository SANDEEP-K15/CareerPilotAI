from careerpilot.application.jobs.ingest_types import IngestOutcome, IngestRawJobResult
from careerpilot.application.jobs.normalization import job_from_raw, jobs_are_equivalent

__all__ = [
    "IngestOutcome",
    "IngestRawJobResult",
    "job_from_raw",
    "jobs_are_equivalent",
]
