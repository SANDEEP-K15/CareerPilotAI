from __future__ import annotations

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.ports.llm import LlmMessage, LlmRole


def build_resume_tailoring_messages(
    profile: CareerProfile,
    job: Job,
    resume: Resume,
) -> tuple[LlmMessage, ...]:
    system = (
        "You tailor a resume for a specific job. Reply with a single JSON object only. "
        'Use keys: "tailored_content" (full resume text as a string), '
        '"changes" (array of objects with "section" and "description" strings). '
        "Preserve factual accuracy. Do not invent employers, degrees, or dates. "
        "Rephrase and emphasize relevant experience only."
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
    resume_lines = [
        "Active resume (version {version}):",
        resume.content,
    ]
    resume_block = resume_lines[0].format(version=resume.version) + "\n" + resume_lines[1]
    return "\n".join([*profile_lines, "", *job_lines, "", resume_block])
