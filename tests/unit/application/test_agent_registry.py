from __future__ import annotations

import pytest
from tests.fakes.agent import StubAgent

from careerpilot.application.agents.errors import (
    DuplicateAgentRegistrationError,
    UnknownAgentError,
)
from careerpilot.application.agents.registry import AgentRegistry
from careerpilot.domain.value_objects.agent_key import AgentKey


def test_empty_registry_is_valid() -> None:
    registry = AgentRegistry()
    assert registry.all() == ()
    assert registry.keys() == ()


def test_register_and_lookup() -> None:
    first = StubAgent("alpha")
    second = StubAgent("beta")
    registry = AgentRegistry((first,))
    registry.register(second)
    assert registry.get("alpha") is first
    assert registry.get(second.agent_key) is second
    assert registry.keys() == (first.agent_key, second.agent_key)


def test_duplicate_registration_is_rejected() -> None:
    registry = AgentRegistry((StubAgent("alpha"),))
    with pytest.raises(DuplicateAgentRegistrationError) as exc:
        registry.register(StubAgent("alpha"))
    assert exc.value.code == "duplicate_agent"


def test_unknown_agent_is_rejected() -> None:
    registry = AgentRegistry()
    with pytest.raises(UnknownAgentError) as exc:
        registry.get("missing_agent")
    assert exc.value.code == "unknown_agent"


def test_registry_has_no_built_in_agents() -> None:
    registry = AgentRegistry()
    with pytest.raises(UnknownAgentError):
        registry.get("job_search")


def test_resolve_none_returns_all_registered() -> None:
    registry = AgentRegistry((StubAgent("beta"), StubAgent("alpha")))
    resolved = registry.resolve(None)
    assert [port.agent_key.value for port in resolved] == ["alpha", "beta"]
    assert isinstance(resolved[0].agent_key, AgentKey)
