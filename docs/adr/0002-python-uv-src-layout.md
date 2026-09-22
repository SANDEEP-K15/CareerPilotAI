# ADR 0002: Python 3.12, uv, and src layout

## Status

Accepted

## Context

The platform needs reproducible installs, strict typing, and a clear
import boundary between the product package and tests/docs.

## Decision

- Python 3.12+ (`requires-python = ">=3.12"`).
- `uv` with a committed `uv.lock`.
- `src/careerpilot` package layout.
- Ruff for lint, mypy in strict mode, pytest for automated tests.
- FastAPI, SQLAlchemy, Temporal, and similar runtime libraries are added
  when the milestone that uses them lands — not as unused M0 dependencies.

## Consequences

- Contributors install `uv` and run `uv sync --dev`.
- CI uses `uv sync --frozen`.
- Application imports are `from careerpilot...`, never from `src`.
