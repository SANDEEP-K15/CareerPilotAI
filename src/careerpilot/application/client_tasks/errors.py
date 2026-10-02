from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class ClientTaskTimeoutError(ApplicationError):
    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            f"Client task timed out after {timeout_seconds:g} seconds.",
            code="client_task_timeout",
        )
        self.timeout_seconds = timeout_seconds


class ClientTaskServiceUnavailableError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            "Client task submission is not configured.",
            code="client_task_unavailable",
        )
