from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.executions import router as executions_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.api.tools import router as tools_router
from app.config import get_settings
from app.errors import ApiError, api_error_handler
from app.observability import APP_LOGGER, ERROR_LOGGER, REQUEST_LOGGER, configure_logging


async def handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, ApiError):
        request_id = getattr(request.state, "request_id", "unknown")
        level = "error" if exc.status_code >= 500 else "warning"
        getattr(ERROR_LOGGER, level)(
            "api error code=%s status_code=%s path=%s request_id=%s",
            exc.code,
            exc.status_code,
            request.url.path,
            request_id,
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "request_id": request_id,
            },
        )
        return await api_error_handler(request, exc)
    raise exc


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    docs_url = "/docs" if settings.effective_docs_enabled else None
    redoc_url = "/redoc" if settings.effective_docs_enabled else None

    app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url)
    app.add_exception_handler(ApiError, handle_api_error)
    APP_LOGGER.info(
        "application configured environment=%s public_base_url=%s api_base_url=%s cookie_secure=%s",
        settings.environment,
        settings.public_base_url,
        settings.api_base_url,
        settings.effective_cookie_secure,
        extra={
            "environment": settings.environment,
            "public_base_url": settings.public_base_url,
            "api_base_url": settings.api_base_url,
            "cookie_secure": settings.effective_cookie_secure,
        },
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid4().hex}")
        started_at = perf_counter()
        log_extra = {
            "request_id": request.state.request_id,
            "method": request.method,
            "path": request.url.path,
        }
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            REQUEST_LOGGER.exception(
                "request failed method=%s path=%s status_code=500 duration_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                request.state.request_id,
                extra={**log_extra, "status_code": 500, "duration_ms": duration_ms},
            )
            raise
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request.state.request_id
        REQUEST_LOGGER.info(
            "request completed method=%s path=%s status_code=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.state.request_id,
            extra={
                **log_extra,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(me_router, prefix="/api")
    app.include_router(executions_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    return app


app = create_app()
