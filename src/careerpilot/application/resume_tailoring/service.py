from __future__ import annotations

from careerpilot.application.llm.execution import InvokeLlmUseCase, LlmInvocation
from careerpilot.application.resume_tailoring.errors import ResumeTailoringFailedError
from careerpilot.application.resume_tailoring.parse import parse_resume_tailoring_output
from careerpilot.application.resume_tailoring.prompt import build_resume_tailoring_messages
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.entities.resume_tailoring import ResumeTailoringResult
from careerpilot.domain.errors import InvalidResumeError


class ResumeTailoringService:
    """LLM-backed resume tailoring for one profile/job/resume triple."""

    def __init__(self, *, llm: InvokeLlmUseCase) -> None:
        self._llm = llm

    async def tailor(
        self,
        *,
        profile: CareerProfile,
        job: Job,
        resume: Resume,
        correlation_id: str | None = None,
    ) -> ResumeTailoringResult:
        messages = build_resume_tailoring_messages(profile, job, resume)
        result = await self._llm.execute(
            LlmInvocation(
                messages=messages,
                correlation_id=correlation_id,
                user_id=str(profile.user_id),
                task="resume_tailoring",
                metadata={"job_id": str(job.id), "resume_id": str(resume.id)},
            )
        )
        if not result.succeeded or result.response is None:
            raise ResumeTailoringFailedError()
        parsed = parse_resume_tailoring_output(result.response.content)
        if parsed is None:
            raise ResumeTailoringFailedError("Resume tailoring returned invalid structured output.")
        try:
            return ResumeTailoringResult.new(
                user_id=profile.user_id,
                job_id=job.id,
                source_resume_id=resume.id,
                source_resume_version=resume.version,
                tailored_content=parsed.tailored_content,
                changes=parsed.changes,
                llm_provider=result.provider,
                llm_model=result.model.value,
            )
        except InvalidResumeError as exc:
            raise ResumeTailoringFailedError(str(exc.message)) from exc
