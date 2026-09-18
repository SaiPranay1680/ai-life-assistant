from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.actions import Action
from ...models.documents import Document
from ...models.extraction import ExtractionField
from ...models.reminder import Reminder
from ..auth.deps import CurrentUser
from .schemas import ActionOut, ReminderCreate
from .suggest import suggestions_for

REMINDER_DAYS = {
    "Remind me 30 days before": 30,
    "Remind me 14 days before": 14,
    "Remind me 7 days before": 7,
    "Remind me 3 days before": 3,
}


def _public_status(value: str | None) -> str:
    if value == "confirmed":
        return "reminder_set"
    if value == "dismissed":
        return "dismissed"
    return "suggested"


def _to_out(row: Action) -> ActionOut:
    due = row.due_at.isoformat() if row.due_at else ""
    return ActionOut(
        id=row.id,
        title=row.title or "Suggested action",
        action_type=row.action_type or "",
        due_label=row.due_label or due or "—",
        due_date=due,
        priority=row.priority or "medium",
        reason=row.explanation or "",
        evidence=row.evidence or "",
        reminder_default=row.reminder_default or "Remind me 30 days before",
        status=_public_status(row.status),
    )


def _fire_at(due: date | None, days: int) -> datetime:
    today = date.today()
    if due:
        when = due - timedelta(days=days)
        if when < today:
            when = due if due >= today else today
    else:
        when = today + timedelta(days=days)
    return datetime.combine(when, time(9, 0), tzinfo=timezone.utc)


async def _get_owned(db: AsyncSession, user: CurrentUser, action_id: UUID) -> Action:
    result = await db.execute(
        select(Action).where(Action.id == action_id, Action.workspace_id == user.workspace_id)
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    return action


async def list_actions(db: AsyncSession, user: CurrentUser) -> list[ActionOut]:
    await _suggest_from_reviewed(db, user)
    result = await db.execute(
        select(Action)
        .where(
            Action.workspace_id == user.workspace_id,
            Action.status.in_(("suggested", "confirmed")),
        )
        .order_by(Action.due_at.is_(None), Action.due_at.asc(), Action.created_at.desc())
    )
    return [_to_out(row) for row in result.scalars().all()]


async def dismiss_action(db: AsyncSession, user: CurrentUser, action_id: UUID) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    action.status = "dismissed"
    action.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(action)
    return _to_out(action)


async def create_reminder(
    db: AsyncSession,
    user: CurrentUser,
    action_id: UUID,
    payload: ReminderCreate,
) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    if action.status == "dismissed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This action was dismissed.")
    label = (payload.reminder or "").strip()
    days = REMINDER_DAYS.get(label)
    if days is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a valid reminder option.")

    key = f"{action.id}:{days}"
    stmt = (
        insert(Reminder)
        .values(
            workspace_id=user.workspace_id,
            action_id=action.id,
            fire_at=_fire_at(action.due_at, days),
            channel="in_app",
            offset_label=label,
            idempotency_key=key,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )
    await db.execute(stmt)
    action.status = "confirmed"
    action.confirmed_by = user.id
    action.confirmed_at = datetime.now(timezone.utc)
    action.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(action)
    return _to_out(action)


async def _suggest_from_reviewed(db: AsyncSession, user: CurrentUser) -> None:
    docs = await db.execute(
        select(Document).where(
            Document.workspace_id == user.workspace_id,
            Document.processing_status == "reviewed",
        )
    )
    documents = list(docs.scalars().all())
    if not documents:
        return
    ids = [row.id for row in documents]
    field_rows = await db.execute(
        select(ExtractionField).where(
            ExtractionField.workspace_id == user.workspace_id,
            ExtractionField.document_id.in_(ids),
        )
    )
    by_document: dict = {}
    for field in field_rows.scalars().all():
        by_document.setdefault(field.document_id, {})[field.field_name] = field

    for document in documents:
        for suggestion in suggestions_for(document, by_document.get(document.id, {})):
            stmt = (
                insert(Action)
                .values(
                    workspace_id=user.workspace_id,
                    source_document_id=document.id,
                    title=suggestion["title"],
                    action_type=suggestion["action_type"],
                    due_at=suggestion["due_at"],
                    due_label=suggestion["due_label"],
                    priority=suggestion["priority"],
                    status="suggested",
                    confidence=suggestion["confidence"],
                    explanation=suggestion["explanation"],
                    evidence=suggestion["evidence"],
                    reminder_default=suggestion["reminder_default"],
                    requires_confirmation=True,
                )
                .on_conflict_do_nothing(constraint="uq_actions_workspace_document_type")
            )
            await db.execute(stmt)
    await db.commit()
