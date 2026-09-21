from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ActionType = Literal[
    "PAY",
    "RENEW",
    "REGISTER",
    "REVIEW",
    "FOLLOW_UP",
    "KEEP_FOR_RECORDS",
]

ActionStatus = Literal[
    "suggested",
    "confirmed",
    "in_progress",
    "completed",
    "dismissed",
]


class ActionOut(BaseModel):
    id: UUID
    title: str
    action_type: ActionType | str
    due_label: str
    due_date: str
    priority: str
    reason: str
    evidence: str
    reminder_default: str
    status: ActionStatus | str
    confirmed_by: UUID | None = None
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReminderCreate(BaseModel):
    reminder: str
