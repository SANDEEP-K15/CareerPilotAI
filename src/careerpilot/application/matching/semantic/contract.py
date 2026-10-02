"""Structured semantic matching output expected from the LLM."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SemanticLlmOutput:
    alignment_score: int
    summary: str
    concerns: tuple[str, ...] = ()
