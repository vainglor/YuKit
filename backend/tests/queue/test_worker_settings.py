import importlib


def test_worker_settings_uses_configured_redis_url(monkeypatch) -> None:
    import app.queue.worker as worker
    from app.config import get_settings

    monkeypatch.setenv("YUKIT_REDIS_URL", "redis://redis:6379/2")
    get_settings.cache_clear()

    worker = importlib.reload(worker)

    assert worker.WorkerSettings.redis_settings.host == "redis"
    assert worker.WorkerSettings.redis_settings.port == 6379
    assert worker.WorkerSettings.redis_settings.database == 2

    get_settings.cache_clear()
