from __future__ import annotations

from enum import StrEnum


class EmploymentType(StrEnum):
    UNSPECIFIED = "unspecified"
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
