from __future__ import annotations

from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestResult
from careerpilot.domain.entities.job import Job
from careerpilot.ports.agent import AgentOutput


def job_search_agent_output(result: SearchAndIngestResult) -> AgentOutput:
    jobs = tuple(_job_record(job) for job in result.jobs)
    failures = tuple(
        {
            "source": failure.source.value,
            "code": failure.error.code.value,
            "message": failure.error.message,
            "retryable": failure.error.retryable,
        }
        for failure in result.failures
    )
    sources = tuple(
        {
            "source": item.source.value,
            "page": item.page,
            "page_size": item.page_size,
            "returned": item.returned,
            "has_more": item.has_more,
        }
        for item in result.sources
    )
    summary = _summary(len(jobs), len(failures))
    notes: list[str] = []
    if failures:
        notes.append(f"{len(failures)} source(s) reported errors")
    if result.has_more:
        notes.append("more results may be available")
    return AgentOutput(
        summary=summary,
        data={
            "jobs": jobs,
            "job_ids": [record["id"] for record in jobs],
            "page": result.page,
            "page_size": result.page_size,
            "has_more": result.has_more,
            "sources": sources,
            "failures": failures,
        },
        notes=tuple(notes),
    )


def _job_record(job: Job) -> dict[str, object]:
    return {
        "id": str(job.id),
        "source": job.source.value,
        "external_id": job.external_id,
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "remote_policy": job.remote_policy.value,
        "employment_type": job.employment_type.value,
        "status": job.status.value,
    }


def _summary(job_count: int, failure_count: int) -> str:
    if job_count == 0 and failure_count > 0:
        return "Job search completed with source failures and no ingested jobs."
    if job_count == 0:
        return "Job search completed with no matching jobs."
    if failure_count > 0:
        return f"Job search ingested {job_count} job(s) with {failure_count} source failure(s)."
    return f"Job search ingested {job_count} job(s)."
