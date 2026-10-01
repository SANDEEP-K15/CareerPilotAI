"""Deterministic profile-to-job matching. No embeddings, LLMs, or provider fields."""

from __future__ import annotations

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.entities.job_match import DimensionScore, JobMatch
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy

SKILL_WEIGHT = 40
TITLE_WEIGHT = 30
LOCATION_WEIGHT = 15
REMOTE_WEIGHT = 10
EMPLOYMENT_WEIGHT = 5
DEFAULT_THRESHOLD = 40
DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def match_job(profile: CareerProfile, job: Job) -> JobMatch:
    blocked = _hard_filter(profile, job)
    if blocked is not None:
        return JobMatch(
            job_id=job.id,
            score=0,
            passed_filters=False,
            hard_filter=blocked,
            matched_skills=(),
            missing_skills=profile.skills,
            reasons=(),
            concerns=(f"hard filter: {blocked}",),
            dimensions=(),
        )

    matched_skills, missing_skills = _skill_overlap(profile, job)
    skill_score = _ratio(len(matched_skills), len(profile.skills))
    title_score = _title_score(profile, job)
    location_score = _location_score(profile, job)
    remote_score = _policy_score(profile.remote_policy, job.remote_policy)
    employment_score = _policy_score(profile.employment_type, job.employment_type)

    dimensions = (
        DimensionScore("skills", skill_score, SKILL_WEIGHT),
        DimensionScore("title", title_score, TITLE_WEIGHT),
        DimensionScore("location", location_score, LOCATION_WEIGHT),
        DimensionScore("remote", remote_score, REMOTE_WEIGHT),
        DimensionScore("employment", employment_score, EMPLOYMENT_WEIGHT),
    )
    score = (
        skill_score * SKILL_WEIGHT
        + title_score * TITLE_WEIGHT
        + location_score * LOCATION_WEIGHT
        + remote_score * REMOTE_WEIGHT
        + employment_score * EMPLOYMENT_WEIGHT
    ) // 100

    reasons = _reasons(profile, job, matched_skills, title_score, location_score)
    concerns = _concerns(
        missing_skills,
        title_score,
        location_score,
        remote_score,
        employment_score,
    )
    return JobMatch(
        job_id=job.id,
        score=score,
        passed_filters=True,
        hard_filter=None,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        reasons=reasons,
        concerns=concerns,
        dimensions=dimensions,
    )


def rank_matches(
    profile: CareerProfile,
    jobs: tuple[Job, ...],
    *,
    threshold: int = DEFAULT_THRESHOLD,
) -> tuple[JobMatch, ...]:
    scored = tuple(match_job(profile, job) for job in jobs)
    accepted = [item for item in scored if item.passed_filters and item.score >= threshold]
    accepted.sort(key=lambda item: (-item.score, str(item.job_id)))
    return tuple(accepted)


def _hard_filter(profile: CareerProfile, job: Job) -> str | None:
    if job.status is not JobStatus.ACTIVE:
        return "inactive_job"
    if _remote_incompatible(profile.remote_policy, job.remote_policy):
        return "remote_policy"
    if _employment_incompatible(profile.employment_type, job.employment_type):
        return "employment_type"
    if _location_incompatible(profile, job):
        return "location"
    return None


def _remote_incompatible(profile: RemotePolicy, job: RemotePolicy) -> bool:
    if profile is RemotePolicy.UNSPECIFIED or job is RemotePolicy.UNSPECIFIED:
        return False
    if profile == job:
        return False
    return not (profile is RemotePolicy.HYBRID or job is RemotePolicy.HYBRID)


def _employment_incompatible(profile: EmploymentType, job: EmploymentType) -> bool:
    if profile is EmploymentType.UNSPECIFIED or job is EmploymentType.UNSPECIFIED:
        return False
    return profile != job


def _location_incompatible(profile: CareerProfile, job: Job) -> bool:
    if not profile.locations or job.location is None:
        return False
    if job.remote_policy is RemotePolicy.REMOTE:
        return False
    return not _location_overlap(profile.locations, job.location)


def _location_overlap(preferred: tuple[str, ...], job_location: str) -> bool:
    haystack = _fold(job_location)
    for item in preferred:
        needle = _fold(item)
        if needle in haystack or haystack in needle:
            return True
    return False


def _skill_overlap(profile: CareerProfile, job: Job) -> tuple[tuple[str, ...], tuple[str, ...]]:
    haystack = _fold(" ".join(part for part in (job.title, job.description or "") if part))
    matched: list[str] = []
    missing: list[str] = []
    for skill in profile.skills:
        if _fold(skill) in haystack:
            matched.append(skill)
        else:
            missing.append(skill)
    return tuple(matched), tuple(missing)


def _title_score(profile: CareerProfile, job: Job) -> int:
    targets = tuple(item for item in (*profile.target_titles, profile.headline or "") if item)
    if not targets:
        return 0
    job_title = _fold(job.title)
    for target in targets:
        folded = _fold(target)
        if folded in job_title or job_title in folded:
            return 100
    job_tokens = set(job_title.split())
    best = 0
    for target in targets:
        tokens = set(_fold(target).split())
        if not tokens:
            continue
        overlap = len(tokens & job_tokens)
        best = max(best, (overlap * 100) // len(tokens))
    return best


def _location_score(profile: CareerProfile, job: Job) -> int:
    if job.remote_policy is RemotePolicy.REMOTE:
        return 100
    if not profile.locations or job.location is None:
        return 50
    if _location_overlap(profile.locations, job.location):
        return 100
    return 0


def _policy_score(profile_value: object, job_value: object) -> int:
    unspecified = (RemotePolicy.UNSPECIFIED, EmploymentType.UNSPECIFIED)
    if profile_value in unspecified or job_value in unspecified:
        return 50
    if profile_value == job_value:
        return 100
    if RemotePolicy.HYBRID in {profile_value, job_value}:
        return 70
    return 0


def _ratio(matched: int, total: int) -> int:
    if total == 0:
        return 0
    return (matched * 100) // total


def _fold(value: str) -> str:
    return " ".join(value.casefold().split())


def _reasons(
    profile: CareerProfile,
    job: Job,
    matched_skills: tuple[str, ...],
    title_score: int,
    location_score: int,
) -> tuple[str, ...]:
    items: list[str] = []
    if matched_skills:
        items.append("matched skills: " + ", ".join(matched_skills))
    if title_score >= 100:
        items.append(f"title matches a target role ({job.title})")
    elif title_score > 0:
        items.append(f"partial title overlap ({job.title})")
    if location_score == 100 and job.remote_policy is RemotePolicy.REMOTE:
        items.append("job is remote")
    elif location_score == 100 and job.location:
        items.append(f"location matches {job.location}")
    if (
        profile.remote_policy == job.remote_policy
        and job.remote_policy is not RemotePolicy.UNSPECIFIED
    ):
        items.append(f"remote policy matches ({job.remote_policy.value})")
    if (
        profile.employment_type == job.employment_type
        and job.employment_type is not EmploymentType.UNSPECIFIED
    ):
        items.append(f"employment type matches ({job.employment_type.value})")
    return tuple(items)


def _concerns(
    missing_skills: tuple[str, ...],
    title_score: int,
    location_score: int,
    remote_score: int,
    employment_score: int,
) -> tuple[str, ...]:
    items: list[str] = []
    if missing_skills:
        items.append("missing skills: " + ", ".join(missing_skills))
    if title_score == 0:
        items.append("no target-title overlap")
    if location_score == 0:
        items.append("location preference not evidenced")
    if remote_score == 0:
        items.append("remote policy mismatch")
    if employment_score == 0:
        items.append("employment type mismatch")
    return tuple(items)
