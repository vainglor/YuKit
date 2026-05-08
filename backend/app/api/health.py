from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import database_enabled, get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "yukit"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    dependencies: dict[str, str] = {"json_tools": "ok"}

    if database_enabled():
        try:
            sessionmaker = get_sessionmaker()
            async with sessionmaker() as session:
                await session.execute(text("select 1"))
            dependencies["database"] = "ok"
        except Exception:
            dependencies["database"] = "error"
    else:
        dependencies["database"] = "disabled"

    redis_url = get_settings().redis_url
    if redis_url:
        client = Redis.from_url(redis_url, decode_responses=True)
        try:
            await client.ping()
            dependencies["redis"] = "ok"
        except Exception:
            dependencies["redis"] = "error"
        finally:
            await client.aclose()
    else:
        dependencies["redis"] = "disabled"

    status = (
        "ok"
        if all(value in {"ok", "disabled"} for value in dependencies.values())
        else "degraded"
    )
    return {
        "status": status,
        "dependencies": dependencies,
    }
