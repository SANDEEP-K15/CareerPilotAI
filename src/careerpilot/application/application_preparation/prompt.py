from __future__ import annotations

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.ports.llm import LlmMessage, LlmRole


def build_application_prep_messages(
    profile: CareerProfile,
    job: Job,
    resume: Resume,
) -> tuple[LlmMessage, ...]:
    system = (
        "You prepare a candidate for a job application and interview. "
        "Reply with a single JSON object only. "
        'Use keys: "guidance" (concise preparation string), '
        '"talking_points" (array of {"section", "point"} objects linking resume to job), '
        '"interview_questions" (array of {"question", "focus"} likely questions with prep focus). '
        "Base answers only on the provided profile, resume, and job. Do not invent credentials."
    )
    user = _user_payload(profile, job, resume)
    return (
        LlmMessage(role=LlmRole.SYSTEM, content=system),
        LlmMessage(role=LlmRole.USER, content=user),
    )


def _user_payload(profile: CareerProfile, job: Job, resume: Resume) -> str:
    profile_lines = [
        "Profile:",
        f"headline: {profile.headline or ''}",
        f"summary: {profile.summary or ''}",
        f"skills: {', '.join(profile.skills)}",
        f"target_titles: {', '.join(profile.target_titles)}",
    ]
    job_lines = [
        "Target job:",
        f"title: {job.title}",
        f"company: {job.company_name}",
        f"description: {job.description or ''}",
    ]
    resume_block = f"Active resume (version {resume.version}):\n{resume.content}"
    return "\n".join([*profile_lines, "", *job_lines, "", resume_block])
