from __future__ import annotations

from uuid import UUID, uuid4

from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource
from tests.fakes.repositories import InMemoryJobRepository

from careerpilot.application.jobs.ingest_types import IngestOutcome
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSearchQuery, RawJob


def _raw(
    *,
    source: str = "example_board",
    external_id: str = "ext-1",
    title: str = "ML Intern",
    company_name: str = "Acme",
    **kwargs: object,
) -> RawJob:
    return RawJob(
        source=SourceKey.parse(source),
        external_id=external_id,
        title=title,
        company_name=company_name,
        **kwargs,  # type: ignore[arg-type]
    )


def _ingest(
    jobs: InMemoryJobRepository | None = None,
    *,
    job_id: UUID | None = None,
) -> tuple[IngestRawJobUseCase, InMemoryJobRepository]:
    repository = jobs or InMemoryJobRepository()
    use_case = IngestRawJobUseCase(
        jobs=repository,
        clock=FrozenClock(),
        ids=FixedIdGenerator(job_id or uuid4()),
    )
    return use_case, repository


async def test_same_source_and_external_id_is_one_row() -> None:
    job_id = uuid4()
    ingest, jobs = _ingest(job_id=job_id)
    first = await ingest.execute(_raw())
    second = await ingest.execute(_raw(title="ML Intern"))
    assert first.outcome is IngestOutcome.CREATED
    assert second.outcome is IngestOutcome.UNCHANGED
    assert first.job is not None
    assert second.job is not None
    assert first.job.id == second.job.id == job_id
    assert await jobs.get_by_source_identity(SourceKey.parse("example_board"), "ext-1") is first.job


async def test_duplicate_ingestion_does_not_create_a_second_row() -> None:
    ingest, jobs = _ingest()
    raw = _raw(description="Same listing")
    await ingest.execute(raw)
    await ingest.execute(raw)
    stored = await jobs.get_by_source_identity(SourceKey.parse("example_board"), "ext-1")
    assert stored is not None
    assert len(jobs._by_id) == 1


async def test_changed_content_updates_existing_row() -> None:
    job_id = uuid4()
    ingest, jobs = _ingest(job_id=job_id)
    created = await ingest.execute(_raw(title="ML Intern", description="v1"))
    updated = await ingest.execute(_raw(title="Senior ML Intern", description="v2"))
    stored = await jobs.get_by_id(job_id)
    assert created.outcome is IngestOutcome.CREATED
    assert updated.outcome is IngestOutcome.UPDATED
    assert stored is not None
    assert stored.title == "Senior ML Intern"
    assert stored.description == "v2"
    assert stored.id == job_id
    assert stored.discovered_at == FrozenClock().now()
    assert stored.content_hash != created.job.content_hash  # type: ignore[union-attr]


async def test_location_change_updates_even_when_hash_fields_match() -> None:
    ingest, jobs = _ingest()
    await ingest.execute(_raw(location="London"))
    result = await ingest.execute(_raw(location="Manchester"))
    stored = await jobs.get_by_source_identity(SourceKey.parse("example_board"), "ext-1")
    assert result.outcome is IngestOutcome.UPDATED
    assert stored is not None
    assert stored.location == "Manchester"


async def test_multiple_providers_do_not_collapse() -> None:
    jobs = InMemoryJobRepository()
    first = IngestRawJobUseCase(
        jobs=jobs, clock=FrozenClock(), ids=FixedIdGenerator(uuid4(), uuid4())
    )
    a = await first.execute(_raw(source="board_a", external_id="shared", title="Same Title"))
    b = await first.execute(_raw(source="board_b", external_id="shared", title="Same Title"))
    assert a.outcome is IngestOutcome.CREATED
    assert b.outcome is IngestOutcome.CREATED
    assert a.job is not None and b.job is not None
    assert a.job.id != b.job.id
    assert len(jobs._by_id) == 2


async def test_identical_content_from_same_identity_is_unchanged() -> None:
    ingest, _jobs = _ingest()
    raw = _raw(
        source_url="HTTPS://Example.COM/jobs/1",
        title="  ML Intern ",
    )
    created = await ingest.execute(raw)
    again = await ingest.execute(
        _raw(source_url="https://example.com/jobs/1", title="ML Intern")
    )
    assert created.outcome is IngestOutcome.CREATED
    assert again.outcome is IngestOutcome.UNCHANGED


async def test_invalid_raw_job_is_rejected_and_not_persisted() -> None:
    ingest, jobs = _ingest()
    result = await ingest.execute(_raw(title=""))
    assert result.outcome is IngestOutcome.REJECTED
    assert result.job is None
    assert result.reason is not None
    assert len(jobs._by_id) == 0


async def test_malformed_url_is_rejected() -> None:
    ingest, jobs = _ingest()
    result = await ingest.execute(_raw(source_url="not-a-url"))
    assert result.outcome is IngestOutcome.REJECTED
    assert len(jobs._by_id) == 0


async def test_ingest_persists_through_repository() -> None:
    ingest, jobs = _ingest()
    result = await ingest.execute(
        _raw(extra={"provider_field": "kept-as-opaque"})
    )
    assert result.job is not None
    fetched = await jobs.get_by_id(result.job.id)
    assert fetched is not None
    assert fetched.extra == {"provider_field": "kept-as-opaque"}
    by_identity = await jobs.get_by_source_identity(fetched.source, fetched.external_id)
    assert by_identity is fetched


async def test_ingest_uses_fake_job_source_listings() -> None:
    listing = _raw(external_id="from-source", title="From Fake Source")
    source = InMemoryJobSource("example_board", listings=(listing,))
    page = await source.search(JobSearchQuery(keywords=("fake",)))
    ingest, jobs = _ingest()
    assert len(page.items) == 1
    result = await ingest.execute(page.items[0])
    stored = await jobs.get_by_source_identity(SourceKey.parse("example_board"), "from-source")
    assert result.outcome is IngestOutcome.CREATED
    assert stored is not None
    assert stored.title == "From Fake Source"
