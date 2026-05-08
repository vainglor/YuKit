from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import require_current_user
from app.db.models import FavoriteTool, ToolExecution, User, UserPreference
from app.db.session import get_db_session
from app.errors import ApiError

router = APIRouter(prefix="/me", tags=["me"])


class PreferencesRequest(BaseModel):
    tool_options: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] = Field(default_factory=dict)


def require_db(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )
    return db


@router.get("/favorites")
async def list_favorites(
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[str]]:
    db = require_db(db)
    result = await db.execute(
        select(FavoriteTool.tool_name)
        .where(FavoriteTool.user_id == user.id)
        .order_by(FavoriteTool.created_at.desc())
    )
    return {"favorites": list(result.scalars())}


@router.put("/favorites/{tool_name}")
async def add_favorite(
    tool_name: str,
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[str]]:
    db = require_db(db)
    result = await db.execute(
        select(FavoriteTool)
        .where(FavoriteTool.user_id == user.id)
        .where(FavoriteTool.tool_name == tool_name)
    )
    if result.scalar_one_or_none() is None:
        db.add(FavoriteTool(user_id=user.id, tool_name=tool_name))
        await db.commit()
    return await list_favorites(user, db)


@router.delete("/favorites/{tool_name}")
async def remove_favorite(
    tool_name: str,
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[str]]:
    db = require_db(db)
    await db.execute(
        delete(FavoriteTool)
        .where(FavoriteTool.user_id == user.id)
        .where(FavoriteTool.tool_name == tool_name)
    )
    await db.commit()
    return await list_favorites(user, db)


@router.get("/preferences")
async def get_preferences(
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    db = require_db(db)
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user.id))
    preference = result.scalar_one_or_none()
    return {"preferences": preference.preferences if preference else {"tool_options": {}, "ui": {}}}


@router.put("/preferences")
async def update_preferences(
    payload: PreferencesRequest,
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    db = require_db(db)
    value = payload.model_dump()
    result = await db.execute(select(UserPreference).where(UserPreference.user_id == user.id))
    preference = result.scalar_one_or_none()
    if preference is None:
        preference = UserPreference(user_id=user.id, preferences=value)
        db.add(preference)
    else:
        preference.preferences = value
    await db.commit()
    return {"preferences": value}


@router.get("/executions")
async def list_executions(
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    db = require_db(db)
    result = await db.execute(
        select(ToolExecution)
        .where(ToolExecution.user_id == user.id)
        .order_by(ToolExecution.created_at.desc())
        .limit(50)
    )
    executions = [
        {
            "id": item.id,
            "tool": item.tool_name,
            "status": item.status,
            "mode": item.execution_mode,
            "duration_ms": item.duration_ms,
            "created_at": item.created_at.isoformat(),
            "error_code": item.error_code,
            "error_message": item.error_message,
            "result": item.result_json,
        }
        for item in result.scalars()
    ]
    return {"executions": executions}
