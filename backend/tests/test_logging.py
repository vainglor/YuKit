import json
import logging

from fastapi.testclient import TestClient


def test_request_logging_includes_request_id_and_redacts_query(test_app, caplog) -> None:
    caplog.set_level(logging.INFO, logger="yukit.request")

    with TestClient(test_app) as client:
        response = client.get(
            "/api/auth/github/callback?code=secret-code&state=wrong-state",
            headers={"X-Request-ID": "req_test"},
        )

    assert response.status_code == 401
    request_logs = [record for record in caplog.records if record.name == "yukit.request"]
    assert request_logs
    record = request_logs[-1]
    assert record.request_id == "req_test"
    assert record.status_code == 401
    assert record.path == "/api/auth/github/callback"
    assert "secret-code" not in record.getMessage()
    assert "wrong-state" not in record.getMessage()


def test_auth_logging_redacts_oauth_state_and_code(test_app, caplog) -> None:
    from app.config import get_settings

    settings = get_settings()
    settings.github_client_id = "test-client-id"

    caplog.set_level(logging.WARNING, logger="yukit.auth")

    with TestClient(test_app) as client:
        response = client.get("/api/auth/github/callback?code=secret-code&state=wrong-state")

    assert response.status_code == 401
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "OAuth state validation failed" in messages
    assert "secret-code" not in messages
    assert "wrong-state" not in messages


def test_json_log_formatter_outputs_structured_fields() -> None:
    from app.observability import JsonLogFormatter

    record = logging.LogRecord(
        name="yukit.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req_json"
    record.method = "GET"
    record.path = "/api/health"
    record.status_code = 200
    record.duration_ms = 12.34

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "yukit.request"
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "req_json"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.34


def test_api_error_logging_includes_code_without_query_secrets(test_app, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="yukit.error")

    with TestClient(test_app) as client:
        response = client.get(
            "/api/tools/missing?code=secret-code&state=wrong-state",
            headers={"X-Request-ID": "req_error"},
        )

    assert response.status_code == 404
    error_logs = [record for record in caplog.records if record.name == "yukit.error"]
    assert error_logs
    record = error_logs[-1]
    assert record.request_id == "req_error"
    assert record.status_code == 404
    assert record.path == "/api/tools/missing"
    assert "secret-code" not in record.getMessage()
    assert "wrong-state" not in record.getMessage()


def test_configure_logging_supports_json_format() -> None:
    from app.observability import configure_logging

    logger = configure_logging("INFO", "json")
    handler = logger.handlers[0]

    assert handler.formatter.__class__.__name__ == "JsonLogFormatter"


def test_sync_tool_run_logs_metadata_without_input_payload(test_app, caplog) -> None:
    caplog.set_level(logging.INFO, logger="yukit.tool")

    with TestClient(test_app) as client:
        response = client.post(
            "/api/tools/json-format/runs",
            json={
                "input": {"text": '{"secret":"do-not-log"}'},
                "options": {"indent": 2, "sort_keys": True, "ensure_ascii": False},
            },
            headers={"X-Request-ID": "req_tool"},
        )

    assert response.status_code == 200
    tool_logs = [record for record in caplog.records if record.name == "yukit.tool"]
    assert tool_logs
    record = tool_logs[-1]
    assert record.request_id == "req_tool"
    assert record.tool == "json-format"
    assert record.status == "succeeded"
    assert record.mode == "sync"
    assert record.execution_id
    assert "do-not-log" not in record.getMessage()
