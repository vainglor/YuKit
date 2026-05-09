from fastapi.testclient import TestClient


def test_github_callback_rejects_state_mismatch_before_token_exchange(
    test_app,
    monkeypatch,
) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"

    class UnexpectedAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            raise AssertionError("GitHub token exchange should not run on state mismatch")

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", UnexpectedAsyncClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        response = client.get("/api/auth/github/callback?code=fake-code&state=wrong-state")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "oauth_state_mismatch"


def test_dev_login_sets_session_and_current_user(test_app) -> None:
    with TestClient(test_app) as client:
        login_response = client.post(
            "/api/auth/dev-login",
            json={"email": "dev@example.com", "name": "Dev User"},
        )

        assert login_response.status_code == 200
        me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json()["user"]["email"] == "dev@example.com"


def test_auth_options_reports_local_login_availability(test_app) -> None:
    with TestClient(test_app) as client:
        response = client.get("/api/auth/options")

    assert response.status_code == 200
    assert response.json() == {"dev_login": True, "github": False, "email": False}


def test_auth_options_disables_dev_login_in_production(test_app, monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("YUKIT_ENVIRONMENT", "production")
    monkeypatch.setenv("YUKIT_DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("YUKIT_GITHUB_CLIENT_ID", "client-id")
    get_settings.cache_clear()

    with TestClient(test_app) as client:
        response = client.get("/api/auth/options")

    assert response.status_code == 200
    assert response.json() == {"dev_login": False, "github": True, "email": False}


def test_email_login_interface_is_reserved(test_app) -> None:
    with TestClient(test_app) as client:
        response = client.post("/api/auth/email/start", json={"email": "dev@example.com"})

    assert response.status_code == 202
    assert response.json()["status"] == "reserved"


def test_me_resources_require_authentication(test_app) -> None:
    with TestClient(test_app) as client:
        response = client.get("/api/me/favorites")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_required"


def test_user_favorites_preferences_and_history(test_app) -> None:
    with TestClient(test_app) as client:
        client.post("/api/auth/dev-login", json={"email": "dev@example.com", "name": "Dev User"})

        favorite_response = client.put("/api/me/favorites/json-format")
        preferences_response = client.put(
            "/api/me/preferences",
            json={"tool_options": {"json-format": {"indent": 4, "sortKeys": False}}},
        )
        run_response = client.post(
            "/api/tools/json-format/runs",
            json={
                "input": {"text": '{"b":1,"a":2}'},
                "options": {"indent": 4, "sort_keys": True, "ensure_ascii": False},
            },
        )
        favorites = client.get("/api/me/favorites").json()["favorites"]
        preferences = client.get("/api/me/preferences").json()["preferences"]
        executions = client.get("/api/me/executions").json()["executions"]

    assert favorite_response.status_code == 200
    assert preferences_response.status_code == 200
    assert run_response.status_code == 200
    assert favorites == ["json-format"]
    assert preferences["tool_options"]["json-format"]["indent"] == 4
    assert executions[0]["tool"] == "json-format"
    assert executions[0]["status"] == "succeeded"
    assert "input" not in executions[0]
