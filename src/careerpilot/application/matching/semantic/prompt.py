from __future__ import annotations

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.job_match import JobMatch
from careerpilot.ports.llm import LlmMessage, LlmRole


def build_semantic_match_messages(
    profile: CareerProfile,
    job: Job,
    deterministic: JobMatch,
) -> tuple[LlmMessage, ...]:
    system = (
        "You assess job-to-profile fit. Reply with a single JSON object only. "
        'Use keys: "alignment_score" (integer 0-100), "summary" (string), '
        '"concerns" (array of strings, may be empty). '
        "Do not invent credentials or experience not present in the input."
    )
    user = _user_payload(profile, job, deterministic)
    return (
        LlmMessage(role=LlmRole.SYSTEM, content=system),
        LlmMessage(role=LlmRole.USER, content=user),
    )


def _user_payload(profile: CareerProfile, job: Job, deterministic: JobMatch) -> str:
    profile_lines = [
        "Profile:",
        f"headline: {profile.headline or ''}",
        f"summary: {profile.summary or ''}",
        f"skills: {', '.join(profile.skills)}",
        f"target_titles: {', '.join(profile.target_titles)}",
        f"locations: {', '.join(profile.locations)}",
        f"remote_policy: {profile.remote_policy.value}",
        f"employment_type: {profile.employment_type.value}",
    ]
    years = profile.years_experience if profile.years_experience is not None else ""
    profile_lines.append(f"years_experience: {years}")
    job_lines = [
        "Job:",
        f"title: {job.title}",
        f"company: {job.company_name}",
        f"location: {job.location or ''}",
        f"remote_policy: {job.remote_policy.value}",
        f"employment_type: {job.employment_type.value}",
        f"description: {job.description or ''}",
    ]
    score_lines = [
        "Deterministic baseline (M7, for context only):",
        f"score: {deterministic.score}",
        f"matched_skills: {', '.join(deterministic.matched_skills)}",
        f"missing_skills: {', '.join(deterministic.missing_skills)}",
    ]
    return "\n".join([*profile_lines, "", *job_lines, "", *score_lines])
