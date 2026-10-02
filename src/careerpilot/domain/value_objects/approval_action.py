from __future__ import annotations

from enum import StrEnum

from careerpilot.domain.errors import InvalidApprovalRequestError


class ApprovalAction(StrEnum):
    """Sensitive actions that require explicit human approval before M20+ execution."""

    SUBMIT_APPLICATION = "submit_application"

    @classmethod
    def parse(cls, value: str) -> ApprovalAction:
        normalized = value.strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            raise InvalidApprovalRequestError(f"Unknown approval action: {value}.") from exc
