from fastapi.testclient import TestClient


def test_json_tool_run_returns_sync_result(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/json-format/runs",
        json={
            "input": {"text": '{"b":1,"a":2}'},
            "options": {"indent": 2, "sort_keys": True, "ensure_ascii": False},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "json-format"
    assert body["status"] == "succeeded"
    assert body["mode"] == "sync"
    assert body["result"]["formatted"] == '{\n  "a": 2,\n  "b": 1\n}'


def test_json_tool_run_returns_sanitized_error(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/json-format/runs",
        json={"input": {"text": '{"a": }'}, "options": {"indent": 2}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_json"
    assert "line 1 column 7" in body["error"]["message"]


def test_tool_run_returns_sanitized_schema_validation_error(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/json-format/runs",
        json={"input": {"text": ""}, "options": {"indent": 2}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["message"] == "Invalid tool input or options."


def test_tools_metadata_exposes_json_tool(test_app) -> None:
    client = TestClient(test_app)

    response = client.get("/api/tools")

    assert response.status_code == 200
    tools = response.json()["tools"]
    assert tools[0]["name"] == "json-format"
    assert tools[0]["access_level"] == "public"
    assert tools[0]["execution_mode"] == "sync"
