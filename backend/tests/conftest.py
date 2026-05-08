import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

for module_name in list(sys.modules):
    if module_name == "app" or module_name.startswith("app."):
        del sys.modules[module_name]


@pytest.fixture()
async def db_session(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.db.session import dispose_database, get_sessionmaker, init_database, reset_database

    db_path = tmp_path / "yukit-test.db"
    monkeypatch.setenv("YUKIT_ENVIRONMENT", "test")
    monkeypatch.setenv("YUKIT_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("YUKIT_DEV_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    reset_database()
    await init_database()

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session

    await dispose_database()
    reset_database()
    get_settings.cache_clear()


@pytest.fixture()
async def test_app(tmp_path, monkeypatch):
    from app.config import get_settings
    from app.db.session import dispose_database, init_database, reset_database
    from app.main import create_app

    db_path = tmp_path / "yukit-app-test.db"
    monkeypatch.setenv("YUKIT_ENVIRONMENT", "test")
    monkeypatch.setenv("YUKIT_DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("YUKIT_DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("YUKIT_REDIS_URL", "")
    get_settings.cache_clear()
    reset_database()
    await init_database()

    yield create_app()

    await dispose_database()
    reset_database()
    get_settings.cache_clear()
