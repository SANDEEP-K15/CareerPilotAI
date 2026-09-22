from __future__ import annotations

from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import (
    JobSearchPage,
    JobSearchQuery,
    JobSourceCapabilities,
    RawJob,
)


class InMemoryJobSource:
    """Deterministic JobSourcePort for tests. Not a production job provider."""

    def __init__(
        self,
        source: str,
        listings: tuple[RawJob, ...] = (),
        *,
        fail_with: BaseException | None = None,
        capabilities: JobSourceCapabilities | None = None,
    ) -> None:
        self._source_key = SourceKey.parse(source)
        self._listings = listings
        self._fail_with = fail_with
        self._capabilities = capabilities or JobSourceCapabilities()

    @property
    def source_key(self) -> SourceKey:
        return self._source_key

    @property
    def capabilities(self) -> JobSourceCapabilities:
        return self._capabilities

    async def search(self, query: JobSearchQuery) -> JobSearchPage:
        if self._fail_with is not None:
            raise self._fail_with
        matched = tuple(
            listing
            for listing in self._listings
            if listing.source == self._source_key and _matches(listing, query)
        )
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        page_items = matched[start:end]
        return JobSearchPage(
            items=page_items,
            page=query.page,
            page_size=query.page_size,
            has_more=end < len(matched),
        )


def _matches(listing: RawJob, query: JobSearchQuery) -> bool:
    haystack = " ".join(
        part
        for part in (
            listing.title,
            listing.company_name,
            listing.description or "",
            listing.location or "",
        )
        if part
    ).casefold()
    if query.keywords and not all(keyword.casefold() in haystack for keyword in query.keywords):
        return False
    if query.location is not None:
        listing_location = (listing.location or "").casefold()
        if query.location.casefold() not in listing_location:
            return False
    if query.remote_only is True:
        extra_remote = listing.extra.get("remote")
        if extra_remote is not True and "remote" not in haystack:
            return False
    return True
