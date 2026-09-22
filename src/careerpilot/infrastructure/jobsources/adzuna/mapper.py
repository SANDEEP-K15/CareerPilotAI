"""Map Adzuna JSON objects to provider-neutral RawJob values.

Only documented response fields are read. Missing optional fields are omitted,
not invented. Listings without id, title, or company name are dropped.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSearchPage, RawJob

ADZUNA_SOURCE_KEY = SourceKey.parse("adzuna")


def map_search_page(payload: object, *, page: int, page_size: int) -> JobSearchPage:
    if not isinstance(payload, dict):
        raise ValueError("search payload must be an object")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("search payload is missing a results array")

    items = tuple(
        mapped
        for raw in results
        if (mapped := map_listing(raw)) is not None
    )
    return JobSearchPage(
        items=items,
        page=page,
        page_size=page_size,
        has_more=_has_more(payload, page=page, page_size=page_size, item_count=len(items)),
    )


def map_listing(raw: object) -> RawJob | None:
    if not isinstance(raw, dict):
        return None
    external_id = _as_non_empty_str(raw.get("id"))
    title = _as_non_empty_str(raw.get("title"))
    company_name = _company_name(raw.get("company"))
    if external_id is None or title is None or company_name is None:
        return None

    redirect = _as_non_empty_str(raw.get("redirect_url"))
    extra = _optional_extra(raw)
    return RawJob(
        source=ADZUNA_SOURCE_KEY,
        external_id=external_id,
        title=title,
        company_name=company_name,
        source_url=redirect,
        application_url=redirect,
        location=_location_name(raw.get("location")),
        description=_as_non_empty_str(raw.get("description")),
        posted_at=_parse_created(raw.get("created")),
        extra=extra,
    )


def _has_more(payload: dict[str, Any], *, page: int, page_size: int, item_count: int) -> bool:
    count = payload.get("count")
    if isinstance(count, int) and count >= 0:
        return page * page_size < count
    return item_count == page_size


def _company_name(company: object) -> str | None:
    if not isinstance(company, dict):
        return None
    return _as_non_empty_str(company.get("display_name"))


def _location_name(location: object) -> str | None:
    if not isinstance(location, dict):
        return None
    display = _as_non_empty_str(location.get("display_name"))
    if display is not None:
        return display
    area = location.get("area")
    if isinstance(area, list):
        parts = [_as_non_empty_str(part) for part in area]
        joined = ", ".join(part for part in parts if part)
        return joined or None
    return None


def _parse_created(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _optional_extra(raw: dict[str, Any]) -> dict[str, object]:
    extra: dict[str, object] = {}
    for key in ("salary_min", "salary_max", "contract_type", "contract_time"):
        value = raw.get(key)
        if value is not None and isinstance(value, str | int | float | bool):
            extra[key] = value
    predicted = raw.get("salary_is_predicted")
    if predicted in (0, 1, "0", "1", True, False):
        extra["salary_is_predicted"] = predicted in (1, "1", True)
    category = raw.get("category")
    if isinstance(category, dict):
        tag = _as_non_empty_str(category.get("tag"))
        label = _as_non_empty_str(category.get("label"))
        if tag is not None:
            extra["category_tag"] = tag
        if label is not None:
            extra["category_label"] = label
    return extra


def _as_non_empty_str(value: object) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        return None
    trimmed = " ".join(value.split())
    return trimmed or None
