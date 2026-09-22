from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from careerpilot.infrastructure.persistence.postgres.database import to_sync_postgres_url

pytestmark = pytest.mark.integration


def test_alembic_upgrade_creates_users_and_jobs(migrated_database: str) -> None:
    engine = create_engine(to_sync_postgres_url(migrated_database))
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"users", "jobs", "alembic_version"}.issubset(tables)
        with engine.connect() as connection:
            version = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert version == "m1_001_users_jobs"
        unique = {item["name"] for item in inspector.get_unique_constraints("jobs")}
        assert "uq_jobs_source_external_id" in unique
        indexes = {item["name"] for item in inspector.get_indexes("jobs")}
        assert {"ix_jobs_content_hash", "ix_jobs_posted_at", "ix_jobs_status"}.issubset(indexes)
    finally:
        engine.dispose()
