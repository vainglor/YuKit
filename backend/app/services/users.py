from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import session_expires_at
from app.db.models import AuthIdentity, User, UserSession


async def get_or_create_user(
    db: AsyncSession,
    *,
    email: str,
    display_name: str = "",
    avatar_url: str = "",
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is not None:
        if display_name:
            user.display_name = display_name
        if avatar_url:
            user.avatar_url = avatar_url
        return user

    user = User(email=email, display_name=display_name or email, avatar_url=avatar_url)
    db.add(user)
    await db.flush()
    return user


async def link_identity(
    db: AsyncSession,
    *,
    user: User,
    provider: str,
    provider_user_id: str,
    provider_email: str = "",
) -> None:
    result = await db.execute(
        select(AuthIdentity)
        .where(AuthIdentity.provider == provider)
        .where(AuthIdentity.provider_user_id == provider_user_id)
    )
    identity = result.scalar_one_or_none()
    if identity is None:
        db.add(
            AuthIdentity(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email,
            )
        )


async def create_user_session(db: AsyncSession, user: User) -> UserSession:
    session = UserSession(user_id=user.id, expires_at=session_expires_at())
    db.add(session)
    await db.flush()
    return session
