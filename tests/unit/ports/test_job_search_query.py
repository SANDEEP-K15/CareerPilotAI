from __future__ import annotations

import pytest

from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import InvalidJobSearchQueryError, JobSearchQuery


def test_query_requires_keyword_or_location() -> None:
    with pytest.raises(InvalidJobSearchQueryError) as exc:
        JobSearchQuery()
    assert exc.value.code == "invalid_job_search_query"


def test_query_normalizes_keywords_and_rejects_bad_page() -> None:
    query = JobSearchQuery(keywords=("  ML intern  ",), location="  India  ")
    assert query.keywords == ("ML intern",)
    assert query.location == "India"
    with pytest.raises(InvalidJobSearchQueryError):
        JobSearchQuery(keywords=("ml",), page=0)
    with pytest.raises(InvalidJobSearchQueryError):
        JobSearchQuery(keywords=("ml",), page_size=0)


def test_source_key_stays_provider_neutral() -> None:
    assert SourceKey.parse("memory").value == "memory"
    assert SourceKey.parse("any_board").value == "any_board"
