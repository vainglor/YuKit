from fastapi.testclient import TestClient


def test_regex_tool_run_returns_sync_result(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/regex-test/runs",
        json={
            "input": {"text": "alpha gamma", "pattern": r"\b\w{5}\b"},
            "options": {"flags": [], "max_matches": 10},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "regex-test"
    assert body["status"] == "succeeded"
    assert body["mode"] == "sync"
    assert body["result"]["count"] == 2
    assert body["result"]["matches"][0]["text"] == "alpha"


def test_regex_tool_run_returns_invalid_input_error(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/regex-test/runs",
        json={"input": {"text": "abc", "pattern": "["}, "options": {}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert "Invalid regex pattern" in body["error"]["message"]


def test_tools_metadata_exposes_regex_tool(test_app) -> None:
    client = TestClient(test_app)

    response = client.get("/api/tools")

    assert response.status_code == 200
    tool_names = [tool["name"] for tool in response.json()["tools"]]
    assert "regex-test" in tool_names
