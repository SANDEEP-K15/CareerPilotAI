from __future__ import annotations

from careerpilot.application.agents.errors import AgentExecutionError
from careerpilot.application.use_cases.search_and_ingest_jobs import SearchJobsCommand
from careerpilot.ports.agent import AgentInput

_SEARCH_INTENTS = frozenset({"search", "search_jobs"})


def parse_search_command(agent_input: AgentInput) -> SearchJobsCommand:
    params = dict(agent_input.parameters)
    keywords = _keywords(params.get("keywords"))
    if not keywords and agent_input.intent not in _SEARCH_INTENTS:
        keywords = _keywords(agent_input.intent)
    if not keywords:
        keywords = _keywords(params.get("query"))
    location = _optional_text(params.get("location"))
    remote_only = _optional_bool(params.get("remote_only"))
    page = _positive_int(params.get("page"), default=1, field="page")
    page_size = _positive_int(params.get("page_size"), default=20, field="page_size")
    sources = _sources(params.get("sources"))
    if sources is not None and not sources:
        raise AgentExecutionError(
            "sources must not be empty when provided.",
            code="invalid_job_search_query",
        )
    return SearchJobsCommand(
        keywords=keywords,
        location=location,
        remote_only=remote_only,
        page=page,
        page_size=page_size,
        sources=sources,
    )


def _keywords(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        trimmed = " ".join(value.split())
        return (trimmed,) if trimmed else ()
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for raw in value:
            if not isinstance(raw, str):
                raise AgentExecutionError(
                    "keywords must be a string or list of strings.",
                    code="invalid_agent_task",
                )
            trimmed = " ".join(raw.split())
            if trimmed:
                items.append(trimmed)
        return tuple(items)
    raise AgentExecutionError(
        "keywords must be a string or list of strings.",
        code="invalid_agent_task",
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AgentExecutionError("location must be a string.", code="invalid_agent_task")
    trimmed = " ".join(value.split())
    return trimmed or None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise AgentExecutionError("remote_only must be a boolean.", code="invalid_agent_task")


def _positive_int(value: object, *, default: int, field: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentExecutionError(f"{field} must be an integer.", code="invalid_agent_task")
    return value


def _sources(value: object) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip()
        return (trimmed,) if trimmed else ()
    if isinstance(value, (list, tuple)):
        items = tuple(str(item).strip() for item in value if str(item).strip())
        return items
    raise AgentExecutionError(
        "sources must be a string or list of source names.",
        code="invalid_agent_task",
    )
