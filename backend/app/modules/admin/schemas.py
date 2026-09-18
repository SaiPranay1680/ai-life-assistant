from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    is_active: bool | None = None
    email_verified: bool | None = None
    password: str | None = Field(default=None, min_length=4, max_length=72)


class DatabaseTableStats(BaseModel):
    table_name: str
    row_count: int
    total_size: str | None = None


class SystemStatsOut(BaseModel):
    database_connected: bool
    total_users: int
    active_users: int
    admin_users: int
    regular_users: int
    total_documents: int
    documents_by_type: dict[str, int]
    documents_by_status: dict[str, int]
    total_actions: int
    actions_by_status: dict[str, int]
    actions_by_priority: dict[str, int]
    total_reminders: int
    tables: list[DatabaseTableStats]


class AdminDocumentItem(BaseModel):
    id: UUID
    workspace_id: UUID
    uploaded_by: UUID | None = None
    file_name: str
    mime_type: str
    file_size_bytes: int
    document_type: str | None = None
    document_status: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminActionItem(BaseModel):
    id: UUID
    workspace_id: UUID
    document_id: UUID | None = None
    title: str
    action_type: str
    status: str
    priority: str
    due_date: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
