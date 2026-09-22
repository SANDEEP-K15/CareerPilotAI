from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from tests.fakes.clock import FixedIdGenerator, FrozenClock
from tests.fakes.repositories import (
    InMemoryCareerProfileRepository,
    InMemoryJobRepository,
    InMemoryResumeRepository,
    InMemoryUserRepository,
)

from careerpilot.api.app import create_app
from careerpilot.api.deps import ProfileApi
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.application.job_sources.search import SearchRegisteredSourcesUseCase
from careerpilot.application.use_cases.career_profile import (
    GetCareerProfileUseCase,
    SaveCareerProfileUseCase,
)
from careerpilot.application.use_cases.ingest_raw_job import IngestRawJobUseCase
from careerpilot.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from careerpilot.application.use_cases.resume import (
    AddResumeVersionUseCase,
    GetActiveResumeUseCase,
    GetResumeVersionUseCase,
    ListResumeVersionsUseCase,
)
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchAndIngestJobsUseCase


def _client() -> tuple[TestClient, InMemoryUserRepository]:
    users = InMemoryUserRepository()
    profiles = InMemoryCareerProfileRepository()
    resumes = InMemoryResumeRepository()
    clock = FrozenClock()
    ids = FixedIdGenerator(*[uuid4() for _ in range(32)])
    search = SearchAndIngestJobsUseCase(
        search_sources=SearchRegisteredSourcesUseCase(registry=JobSourceRegistry(())),
        ingest=IngestRawJobUseCase(
            jobs=InMemoryJobRepository(), clock=clock, ids=FixedIdGenerator(uuid4())
        ),
    )
    profile_api = ProfileApi(
        save_profile=SaveCareerProfileUseCase(
            users=users, profiles=profiles, clock=clock, ids=ids
        ),
        get_profile=GetCareerProfileUseCase(profiles=profiles),
        add_resume=AddResumeVersionUseCase(users=users, resumes=resumes, clock=clock, ids=ids),
        get_active_resume=GetActiveResumeUseCase(resumes=resumes),
        get_resume_version=GetResumeVersionUseCase(resumes=resumes),
        list_resumes=ListResumeVersionsUseCase(resumes=resumes),
    )
    return TestClient(create_app(search_jobs=search, profile_api=profile_api)), users


def _add_user(users: InMemoryUserRepository) -> UUID:
    user_id = uuid4()
    asyncio.run(
        RegisterUserUseCase(
            users=users, clock=FrozenClock(), ids=FixedIdGenerator(user_id)
        ).execute(RegisterUserCommand(display_name="Ada"))
    )
    return user_id


def test_profile_api_create_get_update() -> None:
    client, users = _client()
    user_id = _add_user(users)
    created = client.put(
        f"/api/v1/users/{user_id}/profile",
        json={"headline": "ML intern", "skills": ["Python"], "locations": ["Remote"]},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["headline"] == "ML intern"
    assert body["skills"] == ["Python"]
    fetched = client.get(f"/api/v1/users/{user_id}/profile")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    updated = client.put(
        f"/api/v1/users/{user_id}/profile",
        json={"headline": "Senior intern", "skills": ["Python", "SQL"]},
    )
    assert updated.status_code == 200
    assert updated.json()["id"] == body["id"]
    assert updated.json()["headline"] == "Senior intern"


def test_profile_api_validation_and_unknown_user() -> None:
    client, _users = _client()
    missing = client.put(f"/api/v1/users/{uuid4()}/profile", json={"headline": "X"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "user_not_found"
    invalid = client.put(
        f"/api/v1/users/{uuid4()}/profile",
        json={"years_experience": 99, "embedding": [0.1]},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"


def test_profile_api_user_isolation() -> None:
    client, users = _client()
    first = _add_user(users)
    second = _add_user(users)
    client.put(f"/api/v1/users/{first}/profile", json={"skills": ["secret-skill"]})
    other = client.get(f"/api/v1/users/{second}/profile")
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "career_profile_not_found"
    assert "secret-skill" not in str(other.json())


def test_resume_api_versions_and_active() -> None:
    client, users = _client()
    user_id = _add_user(users)
    first = client.post(
        f"/api/v1/users/{user_id}/resumes",
        json={"content": "version one", "label": "draft"},
    )
    second = client.post(f"/api/v1/users/{user_id}/resumes", json={"content": "version two"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    listed = client.get(f"/api/v1/users/{user_id}/resumes")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 2
    assert listed.json()["items"][0]["content"] == "version one"
    active = client.get(f"/api/v1/users/{user_id}/resumes/active")
    assert active.json()["version"] == 2
    assert active.json()["is_active"] is True
    v1 = client.get(f"/api/v1/users/{user_id}/resumes/1")
    assert v1.json()["content"] == "version one"
    assert v1.json()["is_active"] is False


def test_resume_api_empty_content_is_invalid() -> None:
    client, users = _client()
    user_id = _add_user(users)
    response = client.post(f"/api/v1/users/{user_id}/resumes", json={"content": "  "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_resume"


def test_job_search_route_still_works() -> None:
    client, _users = _client()
    response = client.post("/api/v1/jobs/search", json={"keywords": ["intern"]})
    assert response.status_code == 200
    assert response.json()["items"] == []
