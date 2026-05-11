from fastapi.testclient import TestClient


def test_github_start_uses_api_prefixed_callback_url(test_app) -> None:
    import httpx

    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"

    with TestClient(test_app) as client:
        response = client.get("/api/auth/github/start", follow_redirects=False)

    assert response.status_code == 307
    location = httpx.URL(response.headers["location"])
    assert location.params["client_id"] == "test-client-id"
    assert location.params["redirect_uri"] == "http://localhost:8000/api/auth/github/callback"


def test_github_start_uses_subpath_callback_url_and_http_cookie_in_http_production(
    test_app,
) -> None:
    import httpx

    from app.config import get_settings

    settings = get_settings()
    settings.environment = "production"
    settings.github_client_id = "test-client-id"
    settings.api_base_url = "http://120.25.195.126/yukit/api"

    with TestClient(test_app) as client:
        response = client.get("/api/auth/github/start", follow_redirects=False)

    assert response.status_code == 307
    location = httpx.URL(response.headers["location"])
    assert location.params["redirect_uri"] == (
        "http://120.25.195.126/yukit/api/auth/github/callback"
    )
    assert "yukit_oauth_state=" in response.headers["set-cookie"]
    assert "Secure" not in response.headers["set-cookie"]


def test_github_start_uses_secure_cookie_for_https_production(test_app) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.environment = "production"
    settings.github_client_id = "test-client-id"
    settings.api_base_url = "https://tools.example.com/yukit/api"

    with TestClient(test_app) as client:
        response = client.get("/api/auth/github/start", follow_redirects=False)

    assert response.status_code == 307
    assert "yukit_oauth_state=" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]


def test_github_callback_creates_session_from_verified_email(test_app, monkeypatch) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"
    settings.public_base_url = "http://frontend.test"

    class GitHubResponse:
        def __init__(self, payload) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class GitHubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, headers, data):
            assert url == settings.github_oauth_token_url
            assert data["client_id"] == "test-client-id"
            assert data["client_secret"] == "test-client-secret"
            assert data["code"] == "valid-code"
            assert data["state"] == "expected-state"
            assert data["redirect_uri"] == "http://localhost:8000/api/auth/github/callback"
            return GitHubResponse({"access_token": "github-token"})

        async def get(self, url, headers):
            assert headers["Authorization"] == "Bearer github-token"
            if url == settings.github_api_user_url:
                return GitHubResponse(
                    {
                        "id": 12345,
                        "login": "octocat",
                        "name": "Octo Cat",
                        "email": "",
                        "avatar_url": "https://avatars.example/octocat.png",
                    }
                )
            if url == settings.github_api_emails_url:
                return GitHubResponse(
                    [{"email": "octocat@example.com", "primary": True, "verified": True}]
                )
            raise AssertionError(f"Unexpected GitHub API URL: {url}")

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", GitHubClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        callback_response = client.get(
            "/api/auth/github/callback?code=valid-code&state=expected-state",
            follow_redirects=False,
        )
        me_response = client.get("/api/auth/me")

    assert callback_response.status_code == 307
    assert callback_response.headers["location"] == "http://frontend.test"
    assert "yukit_session=" in callback_response.headers["set-cookie"]
    assert me_response.status_code == 200
    user = me_response.json()["user"]
    assert user["email"] == "octocat@example.com"
    assert user["display_name"] == "Octo Cat"
    assert user["avatar_url"] == "https://avatars.example/octocat.png"


def test_github_callback_sets_http_session_cookie_in_http_production(
    test_app,
    monkeypatch,
) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.environment = "production"
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"
    settings.public_base_url = "http://120.25.195.126/yukit"
    settings.api_base_url = "http://120.25.195.126/yukit/api"

    class GitHubResponse:
        def __init__(self, payload) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class GitHubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, headers, data):
            assert data["redirect_uri"] == "http://120.25.195.126/yukit/api/auth/github/callback"
            return GitHubResponse({"access_token": "github-token"})

        async def get(self, url, headers):
            if url == settings.github_api_user_url:
                return GitHubResponse(
                    {
                        "id": 12345,
                        "login": "octocat",
                        "name": "Octo Cat",
                        "email": "octocat@example.com",
                        "avatar_url": "https://avatars.example/octocat.png",
                    }
                )
            raise AssertionError(f"Unexpected GitHub API URL: {url}")

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", GitHubClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        callback_response = client.get(
            "/api/auth/github/callback?code=valid-code&state=expected-state",
            follow_redirects=False,
        )

    assert callback_response.status_code == 307
    assert callback_response.headers["location"] == "http://120.25.195.126/yukit"
    assert "yukit_session=" in callback_response.headers["set-cookie"]
    assert "Secure" not in callback_response.headers["set-cookie"]


def test_github_callback_reports_provider_token_error(test_app, monkeypatch) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "wrong-secret"

    class GitHubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "error": "incorrect_client_credentials",
                "error_description": "The client_id and/or client_secret passed are incorrect.",
            }

    class GitHubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, headers, data):
            return GitHubResponse()

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", GitHubClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        response = client.get(
            "/api/auth/github/callback?code=valid-code&state=expected-state",
            follow_redirects=False,
        )

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "github_oauth_failed"
    assert error["message"] == "GitHub login failed: incorrect_client_credentials"
    assert error["detail"] == {
        "provider_error": "incorrect_client_credentials",
        "provider_error_description": "The client_id and/or client_secret passed are incorrect.",
    }


def test_github_callback_reports_bad_verification_code_without_internal_error(
    test_app,
    monkeypatch,
) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"

    class GitHubResponse:
        status_code = 400

        def json(self):
            return {
                "error": "bad_verification_code",
                "error_description": "The code passed is incorrect or expired.",
            }

    class GitHubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, headers, data):
            return GitHubResponse()

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", GitHubClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        response = client.get(
            "/api/auth/github/callback?code=expired-code&state=expected-state",
            follow_redirects=False,
        )

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "github_oauth_failed"
    assert error["message"] == "GitHub login failed: bad_verification_code"
    assert error["detail"] == {
        "provider_error": "bad_verification_code",
        "provider_error_description": "The code passed is incorrect or expired.",
    }


def test_github_callback_reports_provider_timeout_without_internal_error(
    test_app,
    monkeypatch,
) -> None:
    import httpx

    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"
    settings.github_client_secret = "test-client-secret"

    class GitHubClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, headers, data):
            raise httpx.ConnectTimeout("GitHub token endpoint timed out")

    monkeypatch.setattr("app.api.auth.httpx.AsyncClient", GitHubClient)

    with TestClient(test_app) as client:
        client.cookies.set("yukit_oauth_state", "expected-state")
        response = client.get(
            "/api/auth/github/callback?code=valid-code&state=expected-state",
            follow_redirects=False,
        )

    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "github_oauth_provider_unavailable"
    assert error["message"] == "GitHub OAuth provider is unavailable."


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


def test_auth_options_reports_local_login_availability(test_app, monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("YUKIT_GITHUB_CLIENT_ID", "")
    get_settings.cache_clear()

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
