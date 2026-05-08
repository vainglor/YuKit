from fastapi.testclient import TestClient


def test_timestamp_tool_run_returns_sync_result(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/timestamp/runs",
        json={
            "input": {"text": "1700000000"},
            "options": {"mode": "from-unix"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "timestamp"
    assert body["status"] == "succeeded"
    assert body["mode"] == "sync"
    assert body["result"]["iso_utc"] == "2023-11-14T22:13:20Z"
    assert body["result"]["unix_seconds"] == 1_700_000_000


def test_timestamp_tool_run_returns_invalid_input_error(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/timestamp/runs",
        json={"input": {"text": "not a timestamp"}, "options": {"mode": "from-unix"}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert "Invalid timestamp input" in body["error"]["message"]


def test_tools_metadata_exposes_timestamp_tool(test_app) -> None:
    client = TestClient(test_app)

    response = client.get("/api/tools")

    assert response.status_code == 200
    tool_names = [tool["name"] for tool in response.json()["tools"]]
    assert "timestamp" in tool_names
