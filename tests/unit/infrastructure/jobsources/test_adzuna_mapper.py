from __future__ import annotations

from careerpilot.infrastructure.jobsources.adzuna.mapper import map_listing, map_search_page


def _job(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "129698749",
        "title": "Javascript Developer",
        "created": "2013-11-08T18:07:39Z",
        "redirect_url": "https://www.adzuna.co.uk/jobs/land/ad/129698749",
        "description": "JavaScript Developer Corporate ...",
        "company": {"display_name": "Corporate Project Solutions"},
        "location": {"display_name": "Marlow, Buckinghamshire", "area": ["UK", "Buckinghamshire"]},
        "contract_type": "permanent",
        "salary_min": 50000,
        "salary_max": 55000,
        "salary_is_predicted": 0,
        "category": {"tag": "it-jobs", "label": "IT Jobs"},
    }
    payload.update(overrides)
    return payload


def test_map_listing_uses_documented_fields_only() -> None:
    job = map_listing(_job())
    assert job is not None
    assert job.source.value == "adzuna"
    assert job.external_id == "129698749"
    assert job.company_name == "Corporate Project Solutions"
    assert job.application_url == job.source_url
    assert job.posted_at is not None
    assert job.posted_at.tzinfo is not None
    assert job.extra["contract_type"] == "permanent"
    assert job.extra["salary_is_predicted"] is False


def test_map_listing_skips_missing_required_fields() -> None:
    assert map_listing(_job(title="")) is None
    assert map_listing(_job(company={})) is None
    assert map_listing(_job(id=None)) is None
    assert map_listing("not-an-object") is None


def test_map_listing_accepts_numeric_id() -> None:
    job = map_listing(_job(id=42))
    assert job is not None
    assert job.external_id == "42"


def test_map_search_page_pagination_from_count() -> None:
    page = map_search_page(
        {"count": 5, "results": [_job(id="1"), _job(id="2")]},
        page=1,
        page_size=2,
    )
    assert len(page.items) == 2
    assert page.has_more is True
    last = map_search_page(
        {"count": 5, "results": [_job(id="5")]},
        page=3,
        page_size=2,
    )
    assert last.has_more is False


def test_map_search_page_drops_invalid_items() -> None:
    page = map_search_page(
        {"results": [_job(), "bad", _job(title="")]},
        page=1,
        page_size=20,
    )
    assert len(page.items) == 1
