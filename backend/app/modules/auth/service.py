from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.config import settings
from ...core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    verify_password,
)
from ...models.otp import OTP_ACCOUNT_VERIFICATION, OTP_PASSWORD_RESET
from ...models.user import User, UserProfile, Workspace
from ...services import otp as otp_service
from ...services.email import EmailNotConfigured, send_email
from ...services import rate_limit
from .schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    UserOut,
    VerifyOtpRequest,
    VerifyResetOtpResponse,
    WorkspaceOut,
)

logger = logging.getLogger(__name__)

GENERIC_RESET_MESSAGE = "If an account exists for this email address, a password reset OTP has been sent."


def _display_name(email: str, name: str | None) -> str:
    if name and name.strip():
        return name.strip()
    return email.split("@", 1)[0]


def _to_auth_response(user: User, workspace: Workspace, token: str) -> AuthResponse:
    name = (
        user.name
        or (user.profile.display_name if user.profile and user.profile.display_name else None)
        or str(user.email).split("@", 1)[0]
    )
    return AuthResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=str(user.email),
            name=name,
            role=user.role or "user",
            email_verified=bool(user.email_verified),
            workspace=WorkspaceOut(id=workspace.id, name=workspace.name),
        ),
    )


async def _load_user_graph(db: AsyncSession, user_id) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def register(db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
    username = (payload.username or payload.name or "").strip()
    display = _display_name(str(payload.email), username)
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        name=display,
        role="user",
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    db.add(UserProfile(user_id=user.id, display_name=display))
    workspace = Workspace(name=f"{display}'s workspace", owner_user_id=user.id)
    db.add(workspace)
    await db.commit()

    user = await _load_user_graph(db, user.id)
    if user is None or user.workspace is None:
        raise HTTPException(status_code=500, detail="Failed to create workspace.")
    token = create_access_token(user_id=user.id, workspace_id=user.workspace.id, role=user.role or "user")
    _queue_email("account_created", str(user.email), {"name": display})
    await _issue_and_email_otp(
        db,
        user=user,
        otp_type=OTP_ACCOUNT_VERIFICATION,
        email_kind="account_verification",
    )
    return _to_auth_response(user, user.workspace, token)


async def login(db: AsyncSession, payload: LoginRequest) -> AuthResponse:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.email == str(payload.email).lower())
    )
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if user.workspace is None:
        display = (
            user.name
            or (user.profile.display_name if user.profile and user.profile.display_name else None)
            or str(user.email)
        )
        user.workspace = Workspace(name=f"{display}'s workspace", owner_user_id=user.id)
        db.add(user.workspace)

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    user = await _load_user_graph(db, user.id)
    if user is None or user.workspace is None:
        raise HTTPException(status_code=500, detail="Workspace is missing.")
    token = create_access_token(user_id=user.id, workspace_id=user.workspace.id, role=user.role or "user")
    return _to_auth_response(user, user.workspace, token)


async def get_me(db: AsyncSession, user_id) -> UserOut:
    user = await _load_user_graph(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.workspace is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace not found.")
    name = (
        user.name
        or (user.profile.display_name if user.profile and user.profile.display_name else None)
        or str(user.email).split("@", 1)[0]
    )
    return UserOut(
        id=user.id,
        email=str(user.email),
        name=name,
        role=user.role or "user",
        email_verified=bool(user.email_verified),
        workspace=WorkspaceOut(id=user.workspace.id, name=user.workspace.name),
    )


def _queue_email(kind: str, to_email: str, context: dict) -> None:
    try:
        from app.worker.tasks import send_email_task

        send_email_task.delay(kind, to_email, context)
        return
    except Exception:
        logger.warning("Could not enqueue email task")
    try:
        send_email(kind=kind, to_email=to_email, context=context)
    except EmailNotConfigured:
        return
    except Exception:
        logger.warning("Outbound email failed")


def _display_for(user: User) -> str:
    return (
        user.name
        or (user.profile.display_name if user.profile and user.profile.display_name else None)
        or str(user.email).split("@", 1)[0]
    )


async def _issue_and_email_otp(db: AsyncSession, *, user: User, otp_type: str, email_kind: str) -> datetime:
    otp, expires_at = await otp_service.issue_otp(
        db,
        user_id=user.id,
        email=str(user.email),
        otp_type=otp_type,
    )
    _queue_email(
        email_kind,
        str(user.email),
        {
            "name": _display_for(user),
            "otp": otp,
            "expiry_minutes": settings.otp_expiry_minutes,
        },
    )
    return expires_at


async def _user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def _enforce_limit(key: str, *, limit: int, window: int, detail: str) -> None:
    if not await rate_limit.allow_request(key, limit=limit, window_seconds=window):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


async def forgot_password(db: AsyncSession, payload: ForgotPasswordRequest, *, client_key: str) -> MessageResponse:
    await _enforce_limit(
        f"otp:forgot:ip:{client_key}",
        limit=settings.otp_request_limit,
        window=settings.otp_request_window_seconds,
        detail="Too many password reset requests. Try again later.",
    )
    email = str(payload.email).lower()
    await _enforce_limit(
        f"otp:forgot:email:{email}",
        limit=settings.otp_request_limit,
        window=settings.otp_request_window_seconds,
        detail="Too many password reset requests. Try again later.",
    )
    remaining = await rate_limit.cooldown_remaining(f"otp:cooldown:PASSWORD_RESET:{email}")
    if remaining:
        return MessageResponse(
            message=GENERIC_RESET_MESSAGE,
            cooldown_seconds=remaining,
            expires_in_seconds=settings.otp_expiry_minutes * 60,
        )

    user = await _user_by_email(db, email)
    if user and user.is_active and user.password_hash:
        await _issue_and_email_otp(
            db,
            user=user,
            otp_type=OTP_PASSWORD_RESET,
            email_kind="password_reset",
        )
        await rate_limit.set_cooldown(
            f"otp:cooldown:PASSWORD_RESET:{email}",
            settings.otp_resend_cooldown_seconds,
        )
    return MessageResponse(
        message=GENERIC_RESET_MESSAGE,
        expires_in_seconds=settings.otp_expiry_minutes * 60,
        cooldown_seconds=settings.otp_resend_cooldown_seconds,
    )


async def verify_reset_otp(db: AsyncSession, payload: VerifyOtpRequest, *, client_key: str) -> VerifyResetOtpResponse:
    email = str(payload.email).lower()
    await _enforce_limit(
        f"otp:verify:PASSWORD_RESET:{client_key}:{email}",
        limit=settings.otp_verify_limit,
        window=settings.otp_verify_window_seconds,
        detail="Too many OTP checks. Try again later.",
    )
    user = await _user_by_email(db, email)
    if user is None or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=otp_service.GENERIC_OTP_ERROR)
    try:
        await otp_service.verify_otp(
            db,
            user_id=user.id,
            otp=payload.otp,
            otp_type=OTP_PASSWORD_RESET,
        )
    except otp_service.OtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    token = create_password_reset_token(user_id=user.id)
    return VerifyResetOtpResponse(message="OTP verified. You can create a new password.", reset_token=token)


async def reset_password(db: AsyncSession, payload: ResetPasswordRequest) -> ResetPasswordResponse:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )
    try:
        user_id, jti = decode_password_reset_token(payload.reset_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token.",
        )

    ttl = settings.password_reset_token_minutes * 60
    if not await rate_limit.consume_once(f"otp:reset-token:{jti}", ttl_seconds=ttl):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token.",
        )

    user = await db.get(User, user_id)
    if user is None or not user.is_active or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset is not available for this account.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return ResetPasswordResponse(message="Password reset successfully. You can now sign in.")


async def send_verification_otp(db: AsyncSession, user_id, *, client_key: str) -> MessageResponse:
    user = await _load_user_graph(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.email_verified:
        return MessageResponse(message="Your account is already verified.")

    email = str(user.email).lower()
    await _enforce_limit(
        f"otp:verify-send:{client_key}:{email}",
        limit=settings.otp_request_limit,
        window=settings.otp_request_window_seconds,
        detail="Too many verification emails. Try again later.",
    )
    remaining = await rate_limit.cooldown_remaining(f"otp:cooldown:ACCOUNT_VERIFICATION:{email}")
    if remaining:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Please wait {remaining} seconds before requesting another OTP.",
        )

    await _issue_and_email_otp(
        db,
        user=user,
        otp_type=OTP_ACCOUNT_VERIFICATION,
        email_kind="account_verification",
    )
    await rate_limit.set_cooldown(
        f"otp:cooldown:ACCOUNT_VERIFICATION:{email}",
        settings.otp_resend_cooldown_seconds,
    )
    return MessageResponse(
        message="If verification is needed, a code has been sent to your email.",
        expires_in_seconds=settings.otp_expiry_minutes * 60,
        cooldown_seconds=settings.otp_resend_cooldown_seconds,
    )


async def verify_account(db: AsyncSession, user_id, payload: VerifyOtpRequest, *, client_key: str) -> MessageResponse:
    user = await _load_user_graph(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if str(payload.email).lower() != str(user.email).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=otp_service.GENERIC_OTP_ERROR)
    if user.email_verified:
        return MessageResponse(message="Your account is already verified.")

    await _enforce_limit(
        f"otp:verify:ACCOUNT_VERIFICATION:{client_key}:{user.id}",
        limit=settings.otp_verify_limit,
        window=settings.otp_verify_window_seconds,
        detail="Too many OTP checks. Try again later.",
    )
    try:
        await otp_service.verify_otp(
            db,
            user_id=user.id,
            otp=payload.otp,
            otp_type=OTP_ACCOUNT_VERIFICATION,
        )
    except otp_service.OtpError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc

    user.email_verified = True
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return MessageResponse(message="Your account is verified.")
