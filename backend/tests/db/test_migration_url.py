from app.db.migration_url import sync_database_url


def test_sync_database_url_uses_psycopg_for_asyncpg_postgres_url() -> None:
    assert (
        sync_database_url("postgresql+asyncpg://yukit:yukit@postgres:5432/yukit")
        == "postgresql+psycopg://yukit:yukit@postgres:5432/yukit"
    )


def test_sync_database_url_uses_builtin_sqlite_driver_for_aiosqlite_url() -> None:
    assert sync_database_url("sqlite+aiosqlite:///tmp/yukit.db") == "sqlite:///tmp/yukit.db"
