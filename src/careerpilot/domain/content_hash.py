"""Deterministic content hashing for later deduplication (M4)."""

from __future__ import annotations

import hashlib
import json


def job_content_hash(
    *,
    title: str,
    company_name: str,
    description: str | None,
    source_url: str | None,
    application_url: str | None,
) -> str:
    payload = {
        "application_url": _normalize_optional(application_url),
        "company_name": _normalize_required(company_name),
        "description": _normalize_optional(description),
        "source_url": _normalize_optional(source_url),
        "title": _normalize_required(title),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_required(value: str) -> str:
    return " ".join(value.lower().split())


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = " ".join(value.strip().split())
    return stripped.lower() if stripped else None
