from fastapi.testclient import TestClient


def test_production_disables_interactive_docs(monkeypatch) -> None:
    from app.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("YUKIT_ENVIRONMENT", "production")
    monkeypatch.setenv("YUKIT_DOCS_ENABLED", "true")
    get_settings.cache_clear()

    client = TestClient(create_app())

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404

    get_settings.cache_clear()
