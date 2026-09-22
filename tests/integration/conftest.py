from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from careerpilot.config.settings import get_settings
from careerpilot.infrastructure.persistence.postgres.database import (
    create_session_factory,
    to_sync_postgres_url,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_URL = "postgresql+asyncpg://careerpilot:careerpilot@localhost:5432/careerpilot"


def _configured_url() -> str:
    return os.environ.get("DATABASE__URL", DEFAULT_URL)


def _postgres_port_open(host: str = "127.0.0.1", port: int = 5432) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _postgres_available(url: str) -> bool:
    if ("localhost" in url or "127.0.0.1" in url) and not _postgres_port_open():
        return False
    engine = create_engine(
        to_sync_postgres_url(url),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 2},
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = _configured_url()
    if not _postgres_available(url):
        if os.environ.get("CAREERPILOT_RUN_INTEGRATION") == "1":
            pytest.fail(f"PostgreSQL is required but not reachable ({url}).")
        pytest.skip("PostgreSQL is not running; skipping integration tests.")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ["DATABASE__URL"] = url
    get_settings.cache_clear()
    return url


@pytest.fixture(scope="session")
def migrated_database(postgres_url: str) -> Iterator[str]:
    config = Config(str(ROOT / "database" / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield postgres_url


@pytest.fixture
async def db_session(migrated_database: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_database)
    factory = create_session_factory(engine)
    async with factory() as session:
        await session.execute(text("TRUNCATE TABLE users, jobs RESTART IDENTITY CASCADE"))
        await session.commit()
        yield session
        await session.rollback()
    await engine.dispose()
