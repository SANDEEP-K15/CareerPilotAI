from __future__ import annotations

from careerpilot.application.application_preparation.errors import ApplicationPreparationFailedError
from careerpilot.application.application_preparation.parse import parse_application_prep_output
from careerpilot.application.application_preparation.prompt import build_application_prep_messages
from careerpilot.application.llm.execution import InvokeLlmUseCase, LlmInvocation
from careerpilot.domain.entities.application_prep import ApplicationPrepPackage
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.resume import Resume
from careerpilot.domain.errors import InvalidApplicationPrepError


class ApplicationPreparationService:
    """LLM-backed application prep for one profile/job/resume triple."""

    def __init__(self, *, llm: InvokeLlmUseCase) -> None:
        self._llm = llm

    async def prepare(
        self,
        *,
        profile: CareerProfile,
        job: Job,
        resume: Resume,
        correlation_id: str | None = None,
    ) -> ApplicationPrepPackage:
        messages = build_application_prep_messages(profile, job, resume)
        result = await self._llm.execute(
            LlmInvocation(
                messages=messages,
                correlation_id=correlation_id,
                user_id=str(profile.user_id),
                task="application_preparation",
                metadata={"job_id": str(job.id), "resume_id": str(resume.id)},
            )
        )
        if not result.succeeded or result.response is None:
            raise ApplicationPreparationFailedError()
        parsed = parse_application_prep_output(result.response.content)
        if parsed is None:
            raise ApplicationPreparationFailedError(
                "Application preparation returned invalid structured output."
            )
        try:
            return ApplicationPrepPackage.new(
                user_id=profile.user_id,
                job_id=job.id,
                source_resume_id=resume.id,
                source_resume_version=resume.version,
                guidance=parsed.guidance,
                talking_points=parsed.talking_points,
                interview_questions=parsed.interview_questions,
                llm_provider=result.provider,
                llm_model=result.model.value,
            )
        except InvalidApplicationPrepError as exc:
            raise ApplicationPreparationFailedError(str(exc.message)) from exc
