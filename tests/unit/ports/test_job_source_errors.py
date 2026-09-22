from __future__ import annotations

from careerpilot.ports.job_source import (
    JobSourceError,
    JobSourceErrorCode,
    normalize_job_source_failure,
)


def test_timeout_error_is_retryable_timeout() -> None:
    error = normalize_job_source_failure("memory", TimeoutError("late"))
    assert error.code is JobSourceErrorCode.TIMEOUT
    assert error.retryable is True
    assert error.source == "memory"


def test_connection_error_is_unavailable() -> None:
    error = normalize_job_source_failure("memory", ConnectionError("down"))
    assert error.code is JobSourceErrorCode.UNAVAILABLE
    assert error.retryable is True


def test_existing_job_source_error_is_preserved() -> None:
    original = JobSourceError(
        "rate limited",
        code=JobSourceErrorCode.RATE_LIMITED,
        source="memory",
        retryable=True,
    )
    assert normalize_job_source_failure("memory", original) is original


def test_unexpected_exception_is_unknown_and_not_retryable() -> None:
    error = normalize_job_source_failure("memory", RuntimeError("boom"))
    assert error.code is JobSourceErrorCode.UNKNOWN
    assert error.retryable is False
