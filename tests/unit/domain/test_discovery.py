from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from careerpilot.domain.discovery import explain_discovery, select_daily_jobs
from careerpilot.domain.entities.career_profile import CareerProfile
from careerpilot.domain.entities.job import Job
from careerpilot.domain.value_objects.employment_type import EmploymentType
from careerpilot.domain.value_objects.job_status import JobStatus
from careerpilot.domain.value_objects.remote_policy import RemotePolicy
from careerpilot.domain.value_objects.source_key import SourceKey


def _profile(**overrides: object) -> CareerProfile:
    payload: dict[str, object] = {
        "profile_id": uuid4(),
        "user_id": uuid4(),
        "now": datetime(2026, 10, 1, tzinfo=UTC),
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
        "discovered_at": datetime(2026, 10, 1, tzinfo=UTC),
        "description": "Use Python and SQL.",
        "location": "London",
        "remote_policy": RemotePolicy.REMOTE,
        "employment_type": EmploymentType.INTERNSHIP,
    }
    payload.update(overrides)
    return Job.new(**payload)  # type: ignore[arg-type]


def test_positive_match_is_selected_with_a_stable_score() -> None:
    job = _job()
    first = select_daily_jobs(_profile(), (job,))
    second = select_daily_jobs(_profile(), (job,))
    assert first == second
    assert first.considered == 1
    assert first.rejected == 0
    assert first.selections[0].job_id == job.id
    assert first.selections[0].score == 100
    assert first.selections[0].matched_skills == ("Python", "SQL")


def test_partial_skill_match_stays_above_threshold() -> None:
    job = _job(description="Python intern role.")
    chosen = select_daily_jobs(_profile(), (job,))
    assert chosen.selections[0].score == 80
    assert chosen.selections[0].missing_skills == ("SQL",)


def test_remote_and_employment_mismatches_are_rejected() -> None:
    profile = _profile()
    remote = _job(remote_policy=RemotePolicy.ONSITE)
    employment = _job(employment_type=EmploymentType.FULL_TIME)
    chosen = select_daily_jobs(profile, (remote, employment))
    assert chosen.selections == ()
    assert chosen.considered == 2
    assert chosen.rejected == 2


def test_onsite_location_mismatch_is_rejected() -> None:
    profile = _profile(remote_policy=RemotePolicy.ONSITE)
    job = _job(remote_policy=RemotePolicy.ONSITE, location="Berlin")
    chosen = select_daily_jobs(profile, (job,))
    assert chosen.selections == ()
    assert chosen.rejected == 1


def test_below_threshold_is_not_padded() -> None:
    profile = _profile(
        skills=("Python",),
        target_titles=("ML Intern",),
        locations=(),
        remote_policy=RemotePolicy.UNSPECIFIED,
        employment_type=EmploymentType.UNSPECIFIED,
    )
    weak = _job(
        title="Accountant",
        description="Spreadsheets only.",
        location=None,
        remote_policy=RemotePolicy.UNSPECIFIED,
        employment_type=EmploymentType.UNSPECIFIED,
    )
    chosen = select_daily_jobs(profile, (weak,))
    assert chosen.selections == ()
    assert chosen.considered == 1
    assert chosen.rejected == 1
    assert (
        explain_discovery(
            searchable=True, selected=0, limit=20, considered=1, failure_count=0
        )
        == "No jobs met the relevance threshold."
    )


def test_inactive_and_duplicate_jobs_are_not_eligible() -> None:
    active = _job()
    inactive = _job(status=JobStatus.INACTIVE)
    chosen = select_daily_jobs(_profile(), (active, inactive, active))
    assert [item.job_id for item in chosen.selections] == [active.id]
    assert chosen.considered == 1


def test_ranking_is_score_then_job_id_and_caps_at_20() -> None:
    strong = _job()
    partial = _job(description="Python intern role.")
    ranked = select_daily_jobs(_profile(), (partial, strong))
    assert [item.job_id for item in ranked.selections] == [strong.id, partial.id]

    tied = tuple(_job() for _ in range(21))
    capped = select_daily_jobs(_profile(), tied)
    expected = sorted((job.id for job in tied), key=str)[:20]
    assert [item.job_id for item in capped.selections] == expected
    assert capped.considered == 21
    assert capped.rejected == 0
    assert len(capped.selections) == 20


def test_empty_input_explains_missing_results() -> None:
    chosen = select_daily_jobs(_profile(), ())
    assert chosen.selections == ()
    assert chosen.considered == 0
    assert (
        explain_discovery(
            searchable=False, selected=0, limit=20, considered=0, failure_count=0
        )
        == "Profile has no target titles or locations to search."
    )
