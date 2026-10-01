from __future__ import annotations

from careerpilot.domain.entities.job_match import JobMatch
from careerpilot.ports.agent import AgentOutput


def job_ranking_agent_output(
    *,
    threshold: int,
    limit: int,
    considered: int,
    rejected: int,
    matches: tuple[JobMatch, ...],
) -> AgentOutput:
    rankings = tuple(_match_record(item) for item in matches)
    summary = _summary(len(rankings), considered, rejected, threshold)
    notes: list[str] = []
    if rejected > 0:
        notes.append(f"{rejected} job(s) below threshold or filtered")
    if len(rankings) == limit and considered > len(rankings):
        notes.append("results capped by limit")
    return AgentOutput(
        summary=summary,
        data={
            "threshold": threshold,
            "limit": limit,
            "considered": considered,
            "rejected": rejected,
            "rankings": rankings,
            "ranked_job_ids": [record["job_id"] for record in rankings],
        },
        notes=tuple(notes),
    )


def _match_record(match: JobMatch) -> dict[str, object]:
    return {
        "job_id": str(match.job_id),
        "score": match.score,
        "matched_skills": list(match.matched_skills),
        "missing_skills": list(match.missing_skills),
        "reasons": list(match.reasons),
        "concerns": list(match.concerns),
    }


def _summary(ranked: int, considered: int, rejected: int, threshold: int) -> str:
    if considered == 0:
        return "No jobs were provided to rank."
    if ranked == 0:
        return f"No jobs met the relevance threshold ({threshold})."
    return f"Ranked {ranked} job(s) at or above threshold {threshold}."
