from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from tests.fakes.clock import FrozenClock
from tests.fakes.repositories import InMemoryCareerProfileRepository, InMemoryJobRepository

from careerpilot.api.app import create_app
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.match_jobs import MatchJobsUseCase
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


class _Ids:
    def new_id(self) -> UUID:
        return uuid4()


def _search() -> SearchAndIngestJobsUseCase:
    return SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(())),
        ingest=IngestRawJobUseCase(
            jobs=InMemoryJobRepository(), clock=FrozenClock(), ids=_Ids()
        ),
    )


def _client(
    profiles: InMemoryCareerProfileRepository,
    jobs: InMemoryJobRepository,
) -> TestClient:
    return TestClient(
        create_app(
            search_jobs=_search(),
            match_jobs=MatchJobsUseCase(profiles=profiles, jobs=jobs),
        )
    )


def test_match_api_returns_canonical_scores() -> None:
    profiles = InMemoryCareerProfileRepository()
    jobs = InMemoryJobRepository()
    user_id = uuid4()
    profile = CareerProfile.new(
        profile_id=uuid4(),
        user_id=user_id,
        now=datetime(2026, 9, 22, tzinfo=UTC),
        skills=("Python",),
        target_titles=("ML Intern",),
        locations=("London",),
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
    )
    job = Job.new(
        job_id=uuid4(),
        source=SourceKey.parse("example_board"),
        external_id="m1",
        title="ML Intern",
        company_name="Acme",
        discovered_at=datetime(2026, 9, 22, tzinfo=UTC),
        description="Python internship.",
        location="London",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
    )
    asyncio.run(profiles.add(profile))
    asyncio.run(jobs.add(job))
    response = _client(profiles, jobs).get(f"/api/v1/users/{user_id}/matches")
    assert response.status_code == 200
    body = response.json()
    assert body["considered"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["job_id"] == str(job.id)
    assert body["items"][0]["score"] >= 40
    assert set(body["items"][0]) == {
        "job_id",
        "score",
        "matched_skills",
        "missing_skills",
        "reasons",
        "concerns",
    }


def test_match_api_missing_profile() -> None:
    response = _client(InMemoryCareerProfileRepository(), InMemoryJobRepository()).get(
        f"/api/v1/users/{uuid4()}/matches"
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "career_profile_not_found"


def test_match_api_invalid_query() -> None:
    response = _client(InMemoryCareerProfileRepository(), InMemoryJobRepository()).get(
        f"/api/v1/users/{uuid4()}/matches", params={"limit": 0}
    )
    assert response.status_code == 422


def test_job_search_unchanged_without_match_wiring() -> None:
    client = TestClient(create_app(search_jobs=_search()))
    response = client.post("/api/v1/jobs/search", json={"keywords": ["intern"]})
    assert response.status_code == 200
    assert response.json()["items"] == []
