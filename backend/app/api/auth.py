import secrets
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import optional_current_user
from app.auth.sessions import clear_session_cookie, set_session_cookie, sign_session
from app.config import get_settings
from app.db.models import User
from app.db.session import get_db_session
from app.errors import ApiError
from app.services.users import create_user_session, get_or_create_user, link_identity

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    email: EmailStr
    name: str = ""


class EmailStartRequest(BaseModel):
    email: EmailStr


class AuthOptionsResponse(BaseModel):
    dev_login: bool
    github: bool
    email: bool


def serialize_user(user: User | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


@router.get("/me")
async def get_me(user: User | None = Depends(optional_current_user)) -> dict[str, Any]:
    return {"user": serialize_user(user)}


@router.get("/options")
async def auth_options() -> AuthOptionsResponse:
    settings = get_settings()
    return AuthOptionsResponse(
        dev_login=settings.environment != "production" and settings.dev_auth_enabled,
        github=bool(settings.github_client_id),
        email=False,
    )


@router.post("/dev-login")
async def dev_login(
    payload: DevLoginRequest,
    response: Response,
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    settings = get_settings()
    if settings.environment == "production" or not settings.dev_auth_enabled:
        raise ApiError(status_code=404, code="not_found", message="Route not found")
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )

    user = await get_or_create_user(db, email=str(payload.email), display_name=payload.name)
    session = await create_user_session(db, user)
    await db.commit()
    set_session_cookie(response, sign_session(user.id, session.id))
    return {"user": serialize_user(user)}


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    clear_session_cookie(response)
    return {"status": "ok"}


@router.post("/email/start", status_code=202)
async def email_start(_: EmailStartRequest) -> dict[str, str]:
    return {"status": "reserved", "provider": "email"}


@router.post("/email/verify", status_code=501)
async def email_verify() -> dict[str, str]:
    return {"status": "reserved", "provider": "email"}


@router.get("/github/start")
async def github_start(response: Response) -> RedirectResponse:
    settings = get_settings()
    if not settings.github_client_id:
        raise ApiError(
            status_code=503,
            code="github_oauth_unconfigured",
            message="GitHub OAuth is not configured.",
        )

    state = secrets.token_urlsafe(24)
    redirect_uri = f"{str(settings.api_base_url).rstrip('/')}/auth/github/callback"
    url = httpx.URL(settings.github_oauth_authorize_url).copy_merge_params(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
    )
    response = RedirectResponse(str(url))
    response.set_cookie(
        "yukit_oauth_state",
        state,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/",
    )
    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession | None = Depends(get_db_session),
) -> RedirectResponse:
    settings = get_settings()
    expected_state = request.cookies.get("yukit_oauth_state")
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise ApiError(
            status_code=401,
            code="oauth_state_mismatch",
            message="OAuth state validation failed.",
        )
    if db is None:
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )
    if not settings.github_client_id or not settings.github_client_secret:
        raise ApiError(
            status_code=503,
            code="github_oauth_unconfigured",
            message="GitHub OAuth is not configured.",
        )

    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            settings.github_oauth_token_url,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "state": state,
            },
        )
        token_response.raise_for_status()
        token = token_response.json().get("access_token")
        if not token:
            raise ApiError(
                status_code=401,
                code="github_oauth_failed",
                message="GitHub login failed",
            )

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        profile_response = await client.get(settings.github_api_user_url, headers=headers)
        profile_response.raise_for_status()
        profile = profile_response.json()

        email = profile.get("email") or ""
        if not email:
            emails_response = await client.get(settings.github_api_emails_url, headers=headers)
            emails_response.raise_for_status()
            emails = emails_response.json()
            primary = next(
                (item for item in emails if item.get("primary") and item.get("verified")),
                emails[0] if emails else {},
            )
            email = primary.get("email", "")

    if not email:
        raise ApiError(
            status_code=401,
            code="github_email_missing",
            message="GitHub email is unavailable",
        )

    user = await get_or_create_user(
        db,
        email=email,
        display_name=profile.get("name") or profile.get("login") or email,
        avatar_url=profile.get("avatar_url") or "",
    )
    await link_identity(
        db,
        user=user,
        provider="github",
        provider_user_id=str(profile["id"]),
        provider_email=email,
    )
    session = await create_user_session(db, user)
    await db.commit()

    redirect = RedirectResponse(str(settings.public_base_url))
    set_session_cookie(redirect, sign_session(user.id, session.id))
    redirect.delete_cookie("yukit_oauth_state", path="/")
    return redirect
