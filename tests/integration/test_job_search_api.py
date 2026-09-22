from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from careerpilot.api.app import create_app
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.infrastructure.persistence.postgres.repositories import SqlAlchemyJobRepository
from careerpilot.ports.job_source import RawJob
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.job_source import InMemoryJobSource

pytestmark = pytest.mark.integration


async def test_search_api_persists_canonical_job(db_session: AsyncSession) -> None:
    jobs = SqlAlchemyJobRepository(db_session)
    listing = RawJob(
        source=SourceKey.parse("example_board"),
        external_id="api-1",
        title="ML Intern",
        company_name="Acme",
        source_url="https://example.com/jobs/api-1",
    )
    source = InMemoryJobSource("example_board", (listing,))
    use_case = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry((source,))),
        ingest=IngestRawJobUseCase(
            jobs=jobs,
            clock=FrozenClock(),
            ids=FixedIdGenerator(uuid4()),
        ),
    )
    app = create_app(search_jobs=use_case)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/search",
            json={"keywords": ["intern"], "sources": ["example_board"]},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    stored = await jobs.get_by_source_identity(SourceKey.parse("example_board"), "api-1")
    assert stored is not None
    assert stored.title == "ML Intern"
    assert str(stored.id) == body["items"][0]["id"]
