from fastapi.testclient import TestClient


def test_error_envelope_and_response_include_request_id(test_app) -> None:
    request_id = "req_test_request_id"

    with TestClient(test_app) as client:
        response = client.post(
            "/api/tools/json-format/runs",
            headers={"X-Request-ID": request_id},
            json={
                "input": {"text": "{bad json"},
                "options": {"indent": 2, "sort_keys": True, "ensure_ascii": False},
            },
        )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["error"]["request_id"] == request_id
