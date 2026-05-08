from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.executions import router as executions_router
from app.api.health import router as health_router
from app.api.me import router as me_router
from app.api.tools import router as tools_router
from app.config import get_settings
from app.errors import ApiError, api_error_handler


def create_app() -> FastAPI:
    settings = get_settings()
    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None

    app = FastAPI(title=settings.app_name, docs_url=docs_url, redoc_url=redoc_url)
    app.add_exception_handler(ApiError, api_error_handler)
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
