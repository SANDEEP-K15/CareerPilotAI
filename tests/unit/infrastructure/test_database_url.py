from careerpilot.infrastructure.persistence.postgres.database import to_sync_postgres_url


def test_asyncpg_url_converts_to_psycopg() -> None:
    assert (
        to_sync_postgres_url("postgresql+asyncpg://u:p@localhost:5432/db")
        == "postgresql+psycopg://u:p@localhost:5432/db"
    )
