from __future__ import annotations

from dataclasses import dataclass

from careerpilot.application.use_cases.career_profile import (
    GetCareerProfileUseCase,
    SaveCareerProfileUseCase,
)
from careerpilot.application.use_cases.resume import (
    AddResumeVersionUseCase,
    GetActiveResumeUseCase,
    GetResumeVersionUseCase,
    ListResumeVersionsUseCase,
)


@dataclass(frozen=True, slots=True)
class ProfileApi:
    save_profile: SaveCareerProfileUseCase
    get_profile: GetCareerProfileUseCase
    add_resume: AddResumeVersionUseCase
    get_active_resume: GetActiveResumeUseCase
    get_resume_version: GetResumeVersionUseCase
    list_resumes: ListResumeVersionsUseCase
