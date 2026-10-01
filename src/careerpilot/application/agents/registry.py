from __future__ import annotations

from collections.abc import Iterable, Sequence

from careerpilot.application.agents.errors import (
    DuplicateAgentRegistrationError,
    UnknownAgentError,
)
from careerpilot.domain.value_objects.agent_key import AgentKey
from careerpilot.ports.agent import AgentPort


class AgentRegistry:
    """In-process catalog of AgentPort implementations.

    No built-in agents. An empty registry is valid until M10+ registers agents.
    """

    def __init__(self, agents: Iterable[AgentPort] = ()) -> None:
        self._agents: dict[str, AgentPort] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: AgentPort) -> None:
        key = agent.agent_key.value
        if key in self._agents:
            raise DuplicateAgentRegistrationError(key)
        self._agents[key] = agent

    def get(self, agent: str | AgentKey) -> AgentPort:
        key = agent.value if isinstance(agent, AgentKey) else AgentKey.parse(agent).value
        try:
            return self._agents[key]
        except KeyError:
            raise UnknownAgentError(key) from None

    def all(self) -> tuple[AgentPort, ...]:
        return tuple(self._agents[key] for key in sorted(self._agents))

    def keys(self) -> tuple[AgentKey, ...]:
        return tuple(port.agent_key for port in self.all())

    def resolve(self, agents: Sequence[str] | None) -> tuple[AgentPort, ...]:
        if agents is None:
            return self.all()
        return tuple(self.get(name) for name in agents)
