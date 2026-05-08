from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.db.models import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def database_enabled() -> bool:
    return bool(get_settings().database_url)


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if not url:
            raise RuntimeError("Database is not configured")
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_async_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db_session() -> AsyncIterator[AsyncSession | None]:
    if not database_enabled():
        yield None
        return

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


async def init_database() -> None:
    if not database_enabled():
        return
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_database() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
    _engine = None


def reset_database() -> None:
    global _engine, _sessionmaker
    _engine = None
    _sessionmaker = None
