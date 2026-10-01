"""Process entry for the daily discovery worker."""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from careerpilot.application.job_sources.registry import JobSourceRegistry
from careerpilot.config.settings import get_settings
from careerpilot.infrastructure.clock import SystemClock
from careerpilot.infrastructure.ids import Uuid4Generator
from careerpilot.infrastructure.jobsources.adzuna import AdzunaJobSource, AdzunaSettings
from careerpilot.infrastructure.persistence.postgres.database import (
    create_engine,
    create_session_factory,
)
from careerpilot.ports.job_source import JobSourcePort
from careerpilot.worker.activities import DailyDiscoveryActivities
from careerpilot.worker.workflows import DailyJobDiscoveryWorkflow


def configured_sources() -> tuple[JobSourcePort, ...]:
    """Register optional adapters that already have credentials. No new providers."""
    settings = AdzunaSettings()
    if not settings.credentials_configured:
        return ()
    return (AdzunaJobSource(settings),)


async def serve() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal.host, namespace=settings.temporal.namespace)
    engine = create_engine(settings.database)
    activities = DailyDiscoveryActivities(
        sessions=create_session_factory(engine),
        registry=JobSourceRegistry(configured_sources()),
        clock=SystemClock(),
        ids=Uuid4Generator(),
    )
    worker = Worker(
        client,
        task_queue=settings.temporal.task_queue,
        workflows=[DailyJobDiscoveryWorkflow],
        activities=activities.bindings(),
    )
    await worker.run()


def main() -> None:
    asyncio.run(serve())
