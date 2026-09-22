"""Infrastructure adapters. Domain and application must not import this package."""

from careerpilot.infrastructure.clock import SystemClock
from careerpilot.infrastructure.ids import Uuid4Generator

__all__ = ["SystemClock", "Uuid4Generator"]
