from __future__ import annotations

from careerpilot.application.errors import ApplicationError


class UnknownOrchestrationIntentError(ApplicationError):
    def __init__(self, intent: str) -> None:
        super().__init__(
            f"No orchestration plan is defined for intent '{intent}'.",
            code="unknown_orchestration_intent",
        )
        self.intent = intent


class InvalidOrchestrationPlanError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="invalid_orchestration_plan")
