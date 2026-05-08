from datetime import UTC, datetime, timedelta

from fastapi import Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings

SESSION_COOKIE = "yukit_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().session_secret, salt="yukit-session")


def sign_session(user_id: str, session_id: str) -> str:
    return _serializer().dumps({"user_id": user_id, "session_id": session_id})


def read_session(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    try:
        data = _serializer().loads(value, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or not data.get("user_id") or not data.get("session_id"):
        return None
    return {"user_id": str(data["user_id"]), "session_id": str(data["session_id"])}


def session_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)


def set_session_cookie(response: Response, value: str) -> None:
    secure = get_settings().environment == "production"
    response.set_cookie(
        SESSION_COOKIE,
        value,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
