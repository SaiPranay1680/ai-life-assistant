import json

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.actions import Action
from ...models.documents import Document
from ...models.extraction import ExtractionField
from ...models.reminder import Reminder
from ..auth.deps import CurrentUser


def _record(row, fields: tuple[str, ...]) -> dict:
    return {field: getattr(row, field) for field in fields}


async def export_workspace_data(db: AsyncSession, user: CurrentUser) -> bytes:
    """Create a portable export for one workspace without exposing file bytes."""
    documents = list(
        (await db.execute(select(Document).where(Document.workspace_id == user.workspace_id))).scalars().all()
    )
    fields = list(
        (await db.execute(select(ExtractionField).where(ExtractionField.workspace_id == user.workspace_id))).scalars().all()
    )
    actions = list(
        (await db.execute(select(Action).where(Action.workspace_id == user.workspace_id))).scalars().all()
    )
    reminders = list(
        (await db.execute(select(Reminder).where(Reminder.workspace_id == user.workspace_id))).scalars().all()
    )
    payload = {
        "format": "ai-life-assistant.workspace-export.v1",
        "workspace_id": user.workspace_id,
        "documents": [
            _record(row, ("id", "original_filename", "extension", "detected_mime", "file_size", "sha256", "scan_status", "processing_status", "document_type", "created_at", "updated_at"))
            for row in documents
        ],
        "extraction_fields": [
            _record(row, ("id", "document_id", "field_name", "raw_value", "normalized_value", "confidence", "page_number", "evidence_snippet"))
            for row in fields
        ],
        "actions": [
            _record(row, ("id", "source_document_id", "title", "action_type", "due_at", "due_label", "priority", "status", "confidence", "explanation", "evidence", "reminder_default", "requires_confirmation", "confirmed_at", "created_at", "updated_at"))
            for row in actions
        ],
        "reminders": [
            _record(row, ("id", "action_id", "fire_at", "channel", "offset_label", "sent_at", "created_at"))
            for row in reminders
        ],
    }
    return json.dumps(jsonable_encoder(payload), indent=2, sort_keys=True).encode("utf-8")
