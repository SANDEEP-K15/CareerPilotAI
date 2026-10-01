from __future__ import annotations

import pytest

from careerpilot.domain.errors import InvalidAgentError
from careerpilot.domain.value_objects.agent_key import AgentKey


def test_agent_key_normalizes_and_parses() -> None:
    key = AgentKey.parse("Job-Search Agent")
    assert key.value == "job_search_agent"
    assert str(key) == "job_search_agent"


def test_agent_key_rejects_invalid_raw_value() -> None:
    with pytest.raises(InvalidAgentError):
        AgentKey.parse("123bad")


def test_agent_key_rejects_empty_after_normalization() -> None:
    with pytest.raises(InvalidAgentError):
        AgentKey.parse("---")
