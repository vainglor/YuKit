from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_user_identities, serialize_user
from app.auth.permissions import require_current_user, require_current_user_session
from app.db.models import FavoriteTool, ToolExecution, User, UserPreference, UserSession, now_utc
from app.db.session import get_db_session
from app.errors import ApiError

router = APIRouter(prefix="/me", tags=["me"])


class PreferencesRequest(BaseModel):
    tool_options: dict[str, Any] = Field(default_factory=dict)
    ui: dict[str, Any] = Field(default_factory=dict)


class ProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    avatar_url: str = Field(default="", max_length=2048)


def require_db(db: AsyncSession | None) -> AsyncSession:
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )
    return db


def serialize_session(session: UserSession, current_session_id: str) -> dict[str, Any]:
    return {
        "id": session.id,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "revoked_at": session.revoked_at.isoformat() if session.revoked_at else None,
        "is_current": session.id == current_session_id,
    }


@router.put("/profile")
async def update_profile(
    payload: ProfileRequest,
    user: User = Depends(require_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    db = require_db(db)
    display_name = payload.display_name.strip()
    if not display_name:
        raise ApiError(
            status_code=422,
            code="invalid_profile",
            message="Display name is required",
        )
    user.display_name = display_name
    user.avatar_url = payload.avatar_url.strip()
    await db.commit()
    identities = await get_user_identities(db, user)
    return {"user": serialize_user(user, identities)}


@router.get("/sessions")
async def list_sessions(
    user_session: tuple[User, UserSession] = Depends(require_current_user_session),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    db = require_db(db)
    user, current_session = user_session
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .order_by(UserSession.created_at.desc())
        .limit(20)
    )
    return {
        "sessions": [
            serialize_session(session, current_session.id) for session in result.scalars()
        ]
    }


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    user_session: tuple[User, UserSession] = Depends(require_current_user_session),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, list[dict[str, Any]]]:
    db = require_db(db)
    user, current_session = user_session
    now = now_utc()
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user.id)
        .where(UserSession.id != current_session.id)
        .where(UserSession.revoked_at.is_(None))
    )
    for session in result.scalars():
        session.revoked_at = now
    await db.commit()
    return await list_sessions(user_session, db)


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
