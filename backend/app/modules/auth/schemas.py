from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_username_or_name(self):
        val = (self.username or self.name or "").strip()
        if not val:
            raise ValueError("Username is required.")
        if len(val) < 2:
            raise ValueError("Username must be at least 2 characters.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


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
    role: str = "user"
    workspace: WorkspaceOut


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
