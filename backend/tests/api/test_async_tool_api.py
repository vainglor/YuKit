from fastapi.testclient import TestClient


def test_authenticated_async_tool_enqueues_execution(test_app, monkeypatch) -> None:
    enqueued_jobs: list[tuple[str, str, dict, dict]] = []

    class FakePool:
        async def enqueue_job(
            self,
            function_name: str,
            execution_id: str,
            input_payload: dict,
            options_payload: dict,
        ) -> None:
            enqueued_jobs.append((function_name, execution_id, input_payload, options_payload))

        async def aclose(self) -> None:
            return None

    async def fake_get_arq_pool() -> FakePool:
        return FakePool()

    monkeypatch.setattr("app.api.tools.get_arq_pool", fake_get_arq_pool)

    with TestClient(test_app) as client:
        client.post("/api/auth/dev-login", json={"email": "dev@example.com", "name": "Dev User"})
        response = client.post(
            "/api/tools/text-hash/runs",
            json={
                "input": {"text": "YuKit"},
                "options": {"algorithm": "sha256"},
            },
        )

        execution_id = response.json()["execution_id"] if response.status_code == 200 else ""
        execution_response = client.get(f"/api/executions/{execution_id}") if execution_id else None

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["mode"] == "async"
    assert enqueued_jobs == [
        (
            "run_tool_job",
            execution_id,
            {"text": "YuKit"},
            {"algorithm": "sha256"},
        )
    ]
    assert execution_response is not None
    assert execution_response.status_code == 200
    assert execution_response.json()["execution"]["status"] == "queued"


def test_anonymous_async_tool_requires_authentication(test_app) -> None:
    with TestClient(test_app) as client:
        response = client.post(
            "/api/tools/text-hash/runs",
            json={
                "input": {"text": "YuKit"},
                "options": {"algorithm": "sha256"},
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_required"


def test_authenticated_user_can_cancel_queued_execution(test_app, monkeypatch) -> None:
    class FakePool:
        async def enqueue_job(self, *args) -> None:
            return None

        async def aclose(self) -> None:
            return None

    async def fake_get_arq_pool() -> FakePool:
        return FakePool()

    monkeypatch.setattr("app.api.tools.get_arq_pool", fake_get_arq_pool)

    with TestClient(test_app) as client:
        client.post("/api/auth/dev-login", json={"email": "dev@example.com", "name": "Dev User"})
        run_response = client.post(
            "/api/tools/text-hash/runs",
            json={
                "input": {"text": "YuKit"},
                "options": {"algorithm": "sha256"},
            },
        )
        execution_id = run_response.json()["execution_id"]

        cancel_response = client.post(f"/api/executions/{execution_id}/cancel")
        execution_response = client.get(f"/api/executions/{execution_id}")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["execution"]["status"] == "canceled"
    assert execution_response.json()["execution"]["status"] == "canceled"
