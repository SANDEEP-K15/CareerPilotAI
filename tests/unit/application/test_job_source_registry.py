from __future__ import annotations

import pytest
from tests.fakes.job_source import InMemoryJobSource

from careerpilot.application.job_sources.errors import (
    DuplicateJobSourceRegistrationError,
    UnknownJobSourceError,
)
from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSearchQuery, RawJob


def _source(name: str) -> InMemoryJobSource:
    key = SourceKey.parse(name)
    return InMemoryJobSource(
        name,
        (
            RawJob(
                source=key,
                external_id="1",
                title="ML Intern",
                company_name="Acme",
            ),
        ),
    )


def test_empty_registry_is_valid() -> None:
    registry = JobSourceRegistry()
    assert registry.all() == ()
    assert registry.keys() == ()


def test_register_and_lookup() -> None:
    first = _source("alpha")
    second = _source("beta")
    registry = JobSourceRegistry((first,))
    registry.register(second)
    assert registry.get("alpha") is first
    assert registry.get(second.source_key) is second
    assert registry.keys() == (first.source_key, second.source_key)


def test_duplicate_registration_is_rejected() -> None:
    source = _source("alpha")
    registry = JobSourceRegistry((source,))
    with pytest.raises(DuplicateJobSourceRegistrationError) as exc:
        registry.register(_source("alpha"))
    assert exc.value.code == "duplicate_job_source"


def test_unknown_provider_is_rejected() -> None:
    registry = JobSourceRegistry()
    with pytest.raises(UnknownJobSourceError) as exc:
        registry.get("missing_source")
    assert exc.value.code == "unknown_job_source"


def test_registry_has_no_built_in_vendor() -> None:
    registry = JobSourceRegistry()
    with pytest.raises(UnknownJobSourceError):
        registry.get("adzuna")


async def test_resolve_none_returns_all_registered() -> None:
    registry = JobSourceRegistry((_source("beta"), _source("alpha")))
    resolved = registry.resolve(None)
    assert [port.source_key.value for port in resolved] == ["alpha", "beta"]
    page = await resolved[0].search(JobSearchQuery(keywords=("intern",)))
    assert len(page.items) == 1
