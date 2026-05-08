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


async def handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, ApiError):
        return await api_error_handler(request, exc)
    raise exc


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.effective_docs_enabled else None
    redoc_url = "/redoc" if settings.effective_docs_enabled else None

    app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url)
    app.add_exception_handler(ApiError, handle_api_error)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid4().hex}")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
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
