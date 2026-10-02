"""Structured resume tailoring output expected from the LLM."""

from __future__ import annotations

from dataclasses import dataclass

from careerpilot.domain.entities.resume_tailoring import ResumeTailoringChange


@dataclass(frozen=True, slots=True)
class ResumeTailoringLlmOutput:
    tailored_content: str
    changes: tuple[ResumeTailoringChange, ...]
