from fastapi.testclient import TestClient


def test_base64_tool_run_returns_sync_result(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/base64/runs",
        json={
            "input": {"text": "Hello, YuKit"},
            "options": {"mode": "encode", "charset": "utf-8"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "base64"
    assert body["status"] == "succeeded"
    assert body["mode"] == "sync"
    assert body["result"]["text"] == "SGVsbG8sIFl1S2l0"


def test_base64_tool_run_returns_invalid_input_error(test_app) -> None:
    client = TestClient(test_app)
    response = client.post(
        "/api/tools/base64/runs",
        json={"input": {"text": "not base64!?"}, "options": {"mode": "decode"}},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert "Invalid Base64 input" in body["error"]["message"]


def test_tools_metadata_exposes_base64_tool(test_app) -> None:
    client = TestClient(test_app)

    response = client.get("/api/tools")

    assert response.status_code == 200
    tool_names = [tool["name"] for tool in response.json()["tools"]]
    assert "base64" in tool_names
