import secrets
from collections.abc import Iterable
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import optional_current_user
from app.auth.sessions import (
    SESSION_COOKIE,
    clear_session_cookie,
    read_session,
    set_session_cookie,
    sign_session,
)
from app.config import get_settings
from app.db.models import AuthIdentity, User, UserSession, now_utc
from app.db.session import get_db_session
from app.errors import ApiError
from app.observability import AUTH_LOGGER
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


def serialize_user(
    user: User | None,
    identities: Iterable[AuthIdentity] | None = None,
) -> dict[str, Any] | None:
    if user is None:
        return None
    identity_list = list(identities) if identities is not None else list(
        user.__dict__.get("identities") or []
    )
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "identities": [
            {
                "provider": identity.provider,
                "provider_email": identity.provider_email,
                "created_at": identity.created_at.isoformat(),
            }
            for identity in sorted(identity_list, key=lambda item: item.created_at)
        ],
    }


async def get_user_identities(db: AsyncSession, user: User) -> list[AuthIdentity]:
    result = await db.execute(
        select(AuthIdentity)
        .where(AuthIdentity.user_id == user.id)
        .order_by(AuthIdentity.created_at.asc())
    )
    return list(result.scalars())


def github_callback_url() -> str:
    return f"{str(get_settings().api_base_url).rstrip('/')}/auth/github/callback"


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def response_json(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def provider_unavailable_error(request: Request, exc: httpx.HTTPError) -> ApiError:
    AUTH_LOGGER.error(
        "GitHub OAuth provider unavailable error_type=%s request_id=%s",
        exc.__class__.__name__,
        request_id_from(request),
        extra={
            "provider": "github",
            "event": "oauth_provider_unavailable",
            "error_type": exc.__class__.__name__,
            "request_id": request_id_from(request),
        },
    )
    return ApiError(
        status_code=502,
        code="github_oauth_provider_unavailable",
        message="GitHub OAuth provider is unavailable.",
        detail={"provider_error": exc.__class__.__name__},
    )


@router.get("/me")
async def get_me(
    user: User | None = Depends(optional_current_user),
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, Any]:
    identities = await get_user_identities(db, user) if user is not None and db is not None else []
    return {"user": serialize_user(user, identities)}


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
    await link_identity(
        db,
        user=user,
        provider="dev",
        provider_user_id=str(payload.email),
        provider_email=str(payload.email),
    )
    session = await create_user_session(db, user)
    identities = await get_user_identities(db, user)
    await db.commit()
    set_session_cookie(response, sign_session(user.id, session.id))
    return {"user": serialize_user(user, identities)}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession | None = Depends(get_db_session),
) -> dict[str, str]:
    session_data = read_session(request.cookies.get(SESSION_COOKIE))
    if db is not None and session_data is not None:
        result = await db.execute(
            select(UserSession)
            .where(UserSession.id == session_data["session_id"])
            .where(UserSession.user_id == session_data["user_id"])
            .where(UserSession.revoked_at.is_(None))
        )
        session = result.scalar_one_or_none()
        if session is not None:
            session.revoked_at = now_utc()
            await db.commit()
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
    url = httpx.URL(settings.github_oauth_authorize_url).copy_merge_params(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": github_callback_url(),
            "scope": "read:user user:email",
            "state": state,
        }
    )
    response = RedirectResponse(str(url))
    response.set_cookie(
        "yukit_oauth_state",
        state,
        httponly=True,
        secure=settings.effective_cookie_secure,
        samesite="lax",
        path="/",
    )
    AUTH_LOGGER.info(
        "GitHub OAuth start redirect_uri=%s cookie_secure=%s",
        github_callback_url(),
        settings.effective_cookie_secure,
        extra={
            "provider": "github",
            "event": "oauth_start",
            "redirect_uri": github_callback_url(),
            "cookie_secure": settings.effective_cookie_secure,
        },
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
        AUTH_LOGGER.warning(
            "OAuth state validation failed provider=github expected_state_present=%s request_id=%s",
            bool(expected_state),
            request_id_from(request),
            extra={
                "provider": "github",
                "event": "oauth_state_mismatch",
                "expected_state_present": bool(expected_state),
                "request_id": request_id_from(request),
            },
        )
        raise ApiError(
            status_code=401,
            code="oauth_state_mismatch",
            message="OAuth state validation failed.",
        )
    if db is None:
        AUTH_LOGGER.error(
            "OAuth callback database unavailable provider=github request_id=%s",
            request_id_from(request),
            extra={
                "provider": "github",
                "event": "database_unavailable",
                "request_id": request_id_from(request),
            },
        )
        raise ApiError(
            status_code=503,
            code="database_unavailable",
            message="Database is unavailable",
        )
    if not settings.github_client_id or not settings.github_client_secret:
        AUTH_LOGGER.error(
            "GitHub OAuth is not configured request_id=%s",
            request_id_from(request),
            extra={
                "provider": "github",
                "event": "oauth_unconfigured",
                "request_id": request_id_from(request),
            },
        )
        raise ApiError(
            status_code=503,
            code="github_oauth_unconfigured",
            message="GitHub OAuth is not configured.",
        )

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            token_response = await client.post(
                settings.github_oauth_token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "state": state,
                    "redirect_uri": github_callback_url(),
                },
            )
        except httpx.HTTPError as exc:
            raise provider_unavailable_error(request, exc) from exc

        token_payload = response_json(token_response)
        token = token_payload.get("access_token")
        if not token:
            provider_error = token_payload.get("error")
            provider_description = token_payload.get("error_description")
            detail = {}
            status_code = getattr(token_response, "status_code", 200)
            if provider_error:
                detail["provider_error"] = provider_error
            elif status_code >= 400:
                detail["provider_error"] = f"http_{status_code}"
            if provider_description:
                detail["provider_error_description"] = provider_description
            AUTH_LOGGER.warning(
                "GitHub OAuth token exchange failed provider_error=%s request_id=%s",
                provider_error or detail.get("provider_error") or "missing_access_token",
                request_id_from(request),
                extra={
                    "provider": "github",
                    "event": "oauth_token_failed",
                    "provider_error": provider_error
                    or detail.get("provider_error")
                    or "missing_access_token",
                    "request_id": request_id_from(request),
                },
            )
            raise ApiError(
                status_code=401,
                code="github_oauth_failed",
                message=(
                    f"GitHub login failed: {provider_error}"
                    if provider_error
                    else "GitHub login failed"
                ),
                detail=detail,
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
        AUTH_LOGGER.warning(
            "GitHub email is unavailable request_id=%s",
            request_id_from(request),
            extra={
                "provider": "github",
                "event": "github_email_missing",
                "request_id": request_id_from(request),
            },
        )
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
    AUTH_LOGGER.info(
        "GitHub OAuth callback succeeded user_id=%s request_id=%s",
        user.id,
        request_id_from(request),
        extra={
            "provider": "github",
            "event": "oauth_callback_succeeded",
            "user_id": user.id,
            "request_id": request_id_from(request),
        },
    )
    return redirect
