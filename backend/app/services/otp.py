from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.otp import AuthOtpCode

GENERIC_OTP_ERROR = "Invalid or expired OTP."
OTP_ATTEMPTS_EXCEEDED = "Too many incorrect OTP attempts. Request a new code."
OTP_EXPIRED = "This OTP has expired. Request a new code."
OTP_USED = "This OTP has already been used. Request a new code."


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(*, otp: str, user_id: UUID, otp_type: str) -> str:
    material = f"{otp_type}:{user_id}:{otp}".encode("utf-8")
    key = settings.jwt_secret.encode("utf-8")
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def otp_matches(*, otp: str, user_id: UUID, otp_type: str, otp_hash: str) -> bool:
    expected = hash_otp(otp=otp, user_id=user_id, otp_type=otp_type)
    return hmac.compare_digest(expected, otp_hash)


async def invalidate_active(db: AsyncSession, *, user_id: UUID, otp_type: str) -> None:
    now = datetime.now(timezone.utc)
    await db.execute(
        update(AuthOtpCode)
        .where(
            AuthOtpCode.user_id == user_id,
            AuthOtpCode.otp_type == otp_type,
            AuthOtpCode.used_at.is_(None),
        )
        .values(used_at=now)
    )


async def issue_otp(
    db: AsyncSession,
    *,
    user_id: UUID,
    email: str,
    otp_type: str,
) -> tuple[str, datetime]:
    await invalidate_active(db, user_id=user_id, otp_type=otp_type)
    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)
    row = AuthOtpCode(
        user_id=user_id,
        email=email.lower(),
        otp_hash=hash_otp(otp=otp, user_id=user_id, otp_type=otp_type),
        otp_type=otp_type,
        expires_at=expires_at,
        attempt_count=0,
        max_attempts=settings.otp_max_attempts,
    )
    db.add(row)
    await db.commit()
    return otp, expires_at


class OtpError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


async def verify_otp(
    db: AsyncSession,
    *,
    user_id: UUID,
    otp: str,
    otp_type: str,
) -> AuthOtpCode:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(AuthOtpCode)
        .where(
            AuthOtpCode.user_id == user_id,
            AuthOtpCode.otp_type == otp_type,
        )
        .order_by(AuthOtpCode.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise OtpError(GENERIC_OTP_ERROR)
    if row.used_at is not None:
        raise OtpError(OTP_USED)
    if row.expires_at <= now:
        raise OtpError(OTP_EXPIRED)
    if row.attempt_count >= row.max_attempts:
        raise OtpError(OTP_ATTEMPTS_EXCEEDED)

    if not otp_matches(otp=otp.strip(), user_id=user_id, otp_type=otp_type, otp_hash=row.otp_hash):
        row.attempt_count += 1
        await db.commit()
        if row.attempt_count >= row.max_attempts:
            raise OtpError(OTP_ATTEMPTS_EXCEEDED)
        raise OtpError(GENERIC_OTP_ERROR)

    row.used_at = now
    await db.commit()
    return row
