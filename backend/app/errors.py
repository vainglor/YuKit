from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    detail: dict[str, Any] | None = None


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail or {},
                "request_id": request_id,
            }
        },
    )
