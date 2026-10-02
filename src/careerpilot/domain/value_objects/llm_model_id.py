"""Opaque model identifier as reported by an LLM provider adapter."""

from __future__ import annotations

import re
from dataclasses import dataclass

from careerpilot.domain.errors import InvalidLlmModelError

_MODEL_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/+-]{0,126}$")


@dataclass(frozen=True, slots=True)
class LlmModelId:
    value: str

    def __post_init__(self) -> None:
        trimmed = self.value.strip()
        if not trimmed or not _MODEL_ID.fullmatch(trimmed):
            raise InvalidLlmModelError(
                "model id must be a non-empty provider-reported identifier."
            )
        object.__setattr__(self, "value", trimmed)

    @classmethod
    def parse(cls, raw: str) -> LlmModelId:
        return cls(value=raw.strip())

    def __str__(self) -> str:
        return self.value
