from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class DuplicateAgentRegistrationError(ApplicationError):
    def __init__(self, agent: str) -> None:
        super().__init__(
            f"Agent '{agent}' is already registered.",
            code="duplicate_agent",
        )
        self.agent = agent


class UnknownAgentError(ApplicationError):
    def __init__(self, agent: str) -> None:
        super().__init__(
            f"Agent '{agent}' is not registered.",
            code="unknown_agent",
        )
        self.agent = agent


class InvalidAgentTaskError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_agent_task")


class AgentExecutionError(ApplicationError):
    """Expected agent failure with a stable code."""

    def __init__(self, message: str, *, code: str = "agent_execution_failed") -> None:
        super().__init__(message, code=code)


def normalize_agent_failure(agent: str, exc: BaseException) -> AgentExecutionError:
    if isinstance(exc, AgentExecutionError):
        return exc
    if isinstance(exc, ApplicationError):
        return AgentExecutionError(exc.message, code=exc.code)
    return AgentExecutionError(
        "Agent execution failed.",
        code="agent_execution_failed",
    )
