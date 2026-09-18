from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=6, max_length=72)
    confirm_password: str = Field(min_length=6, max_length=72)


class ResetPasswordResponse(BaseModel):
    message: str


class WorkspaceOut(BaseModel):
    id: UUID
    name: str


class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    workspace: WorkspaceOut


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
