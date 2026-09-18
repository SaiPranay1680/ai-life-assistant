from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class WorkspaceOut(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileOut(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None
    locale: str | None = None
    timezone: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    id: UUID
    email: str
    name: str | None = None
    role: str = "user"
    is_active: bool = True
    email_verified: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    profile: UserProfileOut | None = None
    workspace: WorkspaceOut | None = None

    model_config = ConfigDict(from_attributes=True)
