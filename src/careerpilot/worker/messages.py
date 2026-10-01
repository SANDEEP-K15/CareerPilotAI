"""Wire types for the daily discovery workflow. No I/O."""

from dataclasses import dataclass, field

LOAD_EXISTING = "load_existing_daily_discovery"
LOAD_PROFILE = "load_discovery_profile"
SEARCH_SOURCES = "search_discovery_sources"
RANK_AND_PERSIST = "rank_and_persist_daily_discovery"


def daily_discovery_workflow_id(user_id: str, run_on: str) -> str:
    return f"daily-job-discovery-{user_id}-{run_on}"


@dataclass
class DailyDiscoveryRequest:
    user_id: str
    run_on: str
    threshold: int = 40
    limit: int = 20


@dataclass
class FailureSnapshot:
    source: str
    code: str
    message: str


@dataclass
class ProfileSnapshot:
    profile_id: str
    searchable: bool


@dataclass
class SearchSnapshot:
    job_ids: list[str] = field(default_factory=list)
    failures: list[FailureSnapshot] = field(default_factory=list)


@dataclass
class PersistDiscoveryRequest:
    user_id: str
    run_on: str
    threshold: int
    limit: int
    searchable: bool
    job_ids: list[str] = field(default_factory=list)
    failures: list[FailureSnapshot] = field(default_factory=list)


@dataclass
class DailyDiscoveryResult:
    found: bool
    discovery_id: str = ""
    selected_job_ids: list[str] = field(default_factory=list)
    considered: int = 0
    rejected: int = 0
    explanation: str = ""
    failure_sources: list[str] = field(default_factory=list)
