"""HTTP(S) URL canonicalization for job listings."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def canonicalize_http_url(value: str | None) -> str | None:
    """Normalize scheme/host casing and drop fragments. Keep path and query.

    Returns None for empty input. Invalid URLs are returned stripped so Job
    validation can reject them; this function does not invent https or hosts.
    """
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    parts = urlsplit(trimmed)
    if not parts.scheme or not parts.netloc:
        return trimmed
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        return trimmed
    path = parts.path if parts.path else ""
    return urlunsplit((scheme, parts.netloc.lower(), path, parts.query, ""))
