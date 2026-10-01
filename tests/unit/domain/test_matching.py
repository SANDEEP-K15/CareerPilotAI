from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.matching import match_job, rank_matches
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


def _profile(**overrides: object) -> CareerProfile:
    payload: dict[str, object] = {
        "profile_id": uuid4(),
        "user_id": uuid4(),
        "now": datetime(2026, 9, 22, tzinfo=UTC),
        "headline": "ML Intern",
        "skills": ("Python", "SQL"),
        "target_titles": ("ML Intern",),
        "locations": ("London",),
        "remote_policy": RemotePolicy.REMOTE,
        "employment_type": EmploymentType.INTERNSHIP,
    }
    payload.update(overrides)
    return CareerProfile.new(**payload)  # type: ignore[arg-type]


def _job(**overrides: object) -> Job:
    payload: dict[str, object] = {
        "job_id": uuid4(),
        "source": SourceKey.parse("example_board"),
        "external_id": str(uuid4()),
        "title": "ML Intern",
        "company_name": "Acme",
        "discovered_at": datetime(2026, 9, 22, tzinfo=UTC),
        "description": "Use Python and SQL daily.",
        "location": "London",
        "remote_policy": RemotePolicy.REMOTE,
        "employment_type": EmploymentType.INTERNSHIP,
    }
    payload.update(overrides)
    return Job.new(**payload)  # type: ignore[arg-type]


def test_positive_match_scores_high_and_explains() -> None:
    result = match_job(_profile(), _job())
    assert result.passed_filters is True
    assert result.score >= 80
    assert result.matched_skills == ("Python", "SQL")
    assert result.missing_skills == ()
    assert any("matched skills" in item for item in result.reasons)
    assert result.hard_filter is None


def test_remote_onsite_is_hard_filtered() -> None:
    result = match_job(
        _profile(remote_policy=RemotePolicy.REMOTE),
        _job(remote_policy=RemotePolicy.ONSITE, location="London"),
    )
    assert result.passed_filters is False
    assert result.score == 0
    assert result.hard_filter == "remote_policy"


def test_employment_mismatch_is_hard_filtered() -> None:
    result = match_job(
        _profile(employment_type=EmploymentType.INTERNSHIP),
        _job(employment_type=EmploymentType.FULL_TIME),
    )
    assert result.passed_filters is False
    assert result.hard_filter == "employment_type"


def test_location_mismatch_for_onsite_is_hard_filtered() -> None:
    result = match_job(
        _profile(locations=("London",), remote_policy=RemotePolicy.UNSPECIFIED),
        _job(location="Manchester", remote_policy=RemotePolicy.ONSITE),
    )
    assert result.passed_filters is False
    assert result.hard_filter == "location"


def test_remote_job_is_not_location_filtered() -> None:
    result = match_job(
        _profile(locations=("London",), remote_policy=RemotePolicy.UNSPECIFIED),
        _job(location="Manchester", remote_policy=RemotePolicy.REMOTE),
    )
    assert result.passed_filters is True


def test_partial_skill_match_reports_missing() -> None:
    result = match_job(
        _profile(skills=("Python", "Kubernetes")),
        _job(description="Build APIs in Python."),
    )
    assert result.passed_filters is True
    assert result.matched_skills == ("Python",)
    assert result.missing_skills == ("Kubernetes",)
    assert any("missing skills" in item for item in result.concerns)


def test_inactive_job_is_rejected() -> None:
    result = match_job(_profile(), _job(status=JobStatus.INACTIVE))
    assert result.passed_filters is False
    assert result.hard_filter == "inactive_job"


def test_unspecified_policies_are_not_hard_filters() -> None:
    result = match_job(
        _profile(
            remote_policy=RemotePolicy.UNSPECIFIED,
            employment_type=EmploymentType.UNSPECIFIED,
            locations=(),
        ),
        _job(
            remote_policy=RemotePolicy.ONSITE,
            employment_type=EmploymentType.FULL_TIME,
            location="Paris",
        ),
    )
    assert result.passed_filters is True


def test_empty_profile_skills_score_zero_for_that_dimension() -> None:
    result = match_job(_profile(skills=(), target_titles=(), headline=None), _job())
    skill = next(item for item in result.dimensions if item.name == "skills")
    title = next(item for item in result.dimensions if item.name == "title")
    assert skill.score == 0
    assert title.score == 0


def test_rank_is_stable_and_thresholded() -> None:
    profile = _profile()
    strong = _job(external_id="strong")
    weak = _job(
        external_id="weak",
        title="Warehouse Associate",
        description="Pack boxes.",
        remote_policy=RemotePolicy.REMOTE,
        employment_type=EmploymentType.INTERNSHIP,
        location="London",
    )
    first = rank_matches(profile, (weak, strong), threshold=40)
    second = rank_matches(profile, (weak, strong), threshold=40)
    assert [item.job_id for item in first] == [item.job_id for item in second]
    assert first[0].job_id == strong.id
    assert all(item.score >= 40 for item in first)


def test_tie_breaks_by_job_id() -> None:
    profile = _profile()
    left = _job(job_id=uuid4(), external_id="a")
    right = _job(job_id=uuid4(), external_id="b")
    ranked = rank_matches(profile, (left, right), threshold=0)
    expected = tuple(sorted((left.id, right.id), key=str))
    assert tuple(item.job_id for item in ranked) == expected or ranked[0].score >= ranked[1].score
    if ranked[0].score == ranked[1].score:
        assert str(ranked[0].job_id) < str(ranked[1].job_id)


def test_hybrid_is_compatible_with_remote() -> None:
    result = match_job(
        _profile(remote_policy=RemotePolicy.HYBRID),
        _job(remote_policy=RemotePolicy.REMOTE),
    )
    assert result.passed_filters is True
    remote = next(item for item in result.dimensions if item.name == "remote")
    assert remote.score == 70
