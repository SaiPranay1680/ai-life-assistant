from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from .deps import get_current_user_id
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
)
from . import service

router = APIRouter(tags=["auth"])


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/auth/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await service.register(db, payload)


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await service.login(db, payload)


@router.post("/auth/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await service.forgot_password(db, payload, client_key=_client_key(request))


@router.post("/auth/verify-reset-otp", response_model=VerifyResetOtpResponse)
async def verify_reset_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await service.verify_reset_otp(db, payload, client_key=_client_key(request))


@router.post("/auth/reset-password", response_model=ResetPasswordResponse)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    return await service.reset_password(db, payload)


@router.post("/auth/send-verification-otp", response_model=MessageResponse)
async def send_verification_otp(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await service.send_verification_otp(db, user_id, client_key=_client_key(request))


@router.post("/auth/verify-account", response_model=MessageResponse)
async def verify_account(
    payload: VerifyOtpRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await service.verify_account(db, user_id, payload, client_key=_client_key(request))


@router.get("/me", response_model=UserOut)
async def me(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_me(db, user_id)
