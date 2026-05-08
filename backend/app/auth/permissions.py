from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import SESSION_COOKIE, read_session
from app.db.models import User, UserSession
from app.db.session import get_db_session
from app.errors import ApiError


async def optional_current_user(
    request: Request,
    db: AsyncSession | None = Depends(get_db_session),
) -> User | None:
    if db is None:
        return None

    session_data = read_session(request.cookies.get(SESSION_COOKIE))
    if session_data is None:
        return None

    result = await db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.id == session_data["session_id"])
        .where(UserSession.user_id == session_data["user_id"])
        .where(UserSession.revoked_at.is_(None))
    )
    row = result.first()
    return row[1] if row else None


async def require_current_user(
    user: User | None = Depends(optional_current_user),
) -> User:
    if user is None:
        raise ApiError(status_code=401, code="auth_required", message="Authentication required")
    return user
