from __future__ import annotations

from collections.abc import Iterable, Sequence

from careerpilot.application.job_sources.errors import (
    DuplicateJobSourceRegistrationError,
    UnknownJobSourceError,
)
from careerpilot.domain.value_objects.source_key import SourceKey
from careerpilot.ports.job_source import JobSourcePort


class JobSourceRegistry:
    """In-process catalog of JobSourcePort implementations.

    No vendor names are built in. An empty registry is a valid configuration.
    """

    def __init__(self, sources: Iterable[JobSourcePort] = ()) -> None:
        self._sources: dict[str, JobSourcePort] = {}
        for source in sources:
            self.register(source)

    def register(self, source: JobSourcePort) -> None:
        key = source.source_key.value
        if key in self._sources:
            raise DuplicateJobSourceRegistrationError(key)
        self._sources[key] = source

    def get(self, source: str | SourceKey) -> JobSourcePort:
        key = source.value if isinstance(source, SourceKey) else SourceKey.parse(source).value
        try:
            return self._sources[key]
        except KeyError:
            raise UnknownJobSourceError(key) from None

    def all(self) -> tuple[JobSourcePort, ...]:
        return tuple(self._sources[key] for key in sorted(self._sources))

    def keys(self) -> tuple[SourceKey, ...]:
        return tuple(port.source_key for port in self.all())

    def resolve(self, sources: Sequence[str] | None) -> tuple[JobSourcePort, ...]:
        if sources is None:
            return self.all()
        return tuple(self.get(name) for name in sources)
