import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from .config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(*, user_id: UUID, workspace_id: UUID, role: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def create_password_reset_token(*, user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_token_minutes)
    payload = {
        "sub": str(user_id),
        "purpose": "password_reset",
        "jti": secrets.token_urlsafe(16),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> tuple[UUID, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired reset token") from exc
    if payload.get("purpose") != "password_reset":
        raise ValueError("Invalid or expired reset token")
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise ValueError("Invalid or expired reset token")
    try:
        return UUID(payload["sub"]), jti
    except (KeyError, ValueError) as exc:
        raise ValueError("Invalid or expired reset token") from exc
