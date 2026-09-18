from uuid import UUID

from pydantic import BaseModel


class ActionOut(BaseModel):
    id: UUID
    title: str
    action_type: str
    due_label: str
    due_date: str
    priority: str
    reason: str
    evidence: str
    reminder_default: str
    status: str

    model_config = {"from_attributes": True}


class ReminderCreate(BaseModel):
    reminder: str
