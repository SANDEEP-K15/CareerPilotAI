"""Optional Adzuna JobSourcePort adapter. Not a platform dependency."""

from careerpilot.infrastructure.jobsources.adzuna.settings import AdzunaSettings
from careerpilot.infrastructure.jobsources.adzuna.source import AdzunaJobSource

__all__ = ["AdzunaJobSource", "AdzunaSettings"]
