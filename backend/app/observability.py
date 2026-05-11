import json
import logging
import sys
from datetime import UTC, datetime
from typing import Literal

REQUEST_LOGGER = logging.getLogger("yukit.request")
AUTH_LOGGER = logging.getLogger("yukit.auth")
APP_LOGGER = logging.getLogger("yukit.app")
ERROR_LOGGER = logging.getLogger("yukit.error")
TOOL_LOGGER = logging.getLogger("yukit.tool")
WORKER_LOGGER = logging.getLogger("yukit.worker")

_STANDARD_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

_SENSITIVE_RECORD_ATTRS = {
    "access_token",
    "authorization",
    "cookie",
    "oauth_code",
    "oauth_state",
    "password",
    "refresh_token",
    "secret",
    "session",
    "state",
    "token",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = "[REDACTED]" if key.lower() in _SENSITIVE_RECORD_ATTRS else value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(
    log_level: str,
    log_format: Literal["text", "json"] = "text",
) -> logging.Logger:
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonLogFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    else:
        for existing_handler in root_logger.handlers:
            existing_handler.setFormatter(formatter)
    root_logger.setLevel(level)
    logging.getLogger("yukit").setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return root_logger
