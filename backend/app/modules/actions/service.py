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
from .constants import LISTABLE_STATUSES, TRANSITIONS
from .schemas import ActionOut, ReminderCreate
from .suggest import suggestions_for

REMINDER_DAYS = {
    "Remind me 30 days before": 30,
    "Remind me 14 days before": 14,
    "Remind me 7 days before": 7,
    "Remind me 3 days before": 3,
}


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
        status=row.status or "suggested",
        confirmed_by=row.confirmed_by,
        confirmed_at=row.confirmed_at,
        completed_at=row.completed_at,
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


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_owned(db: AsyncSession, user: CurrentUser, action_id: UUID) -> Action:
    result = await db.execute(
        select(Action).where(Action.id == action_id, Action.workspace_id == user.workspace_id)
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")
    return action


def _ensure_transition(action: Action, to_status: str) -> None:
    current = action.status or "suggested"
    allowed = TRANSITIONS.get(current, frozenset())
    if to_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move action from '{current}' to '{to_status}'.",
        )


def _mark_confirmed(action: Action, user: CurrentUser) -> None:
    """Set confirmed metadata. Idempotent if already confirmed."""
    if action.status == "suggested":
        action.status = "confirmed"
    if action.confirmed_by is None:
        action.confirmed_by = user.id
    if action.confirmed_at is None:
        action.confirmed_at = _now()
    action.updated_at = _now()


async def list_actions(db: AsyncSession, user: CurrentUser) -> list[ActionOut]:
    await _suggest_from_reviewed(db, user)
    result = await db.execute(
        select(Action)
        .where(
            Action.workspace_id == user.workspace_id,
            Action.status.in_(LISTABLE_STATUSES),
        )
        .order_by(Action.due_at.is_(None), Action.due_at.asc(), Action.created_at.desc())
    )
    return [_to_out(row) for row in result.scalars().all()]


async def confirm_action(db: AsyncSession, user: CurrentUser, action_id: UUID) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    _ensure_transition(action, "confirmed")
    _mark_confirmed(action, user)
    await db.commit()
    await db.refresh(action)
    return _to_out(action)


async def start_action(db: AsyncSession, user: CurrentUser, action_id: UUID) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    _ensure_transition(action, "in_progress")
    # Confirmed metadata should exist before work starts.
    if action.confirmed_by is None:
        action.confirmed_by = user.id
    if action.confirmed_at is None:
        action.confirmed_at = _now()
    action.status = "in_progress"
    action.updated_at = _now()
    await db.commit()
    await db.refresh(action)
    return _to_out(action)


async def complete_action(db: AsyncSession, user: CurrentUser, action_id: UUID) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    _ensure_transition(action, "completed")
    if action.confirmed_by is None:
        action.confirmed_by = user.id
    if action.confirmed_at is None:
        action.confirmed_at = _now()
    action.status = "completed"
    action.completed_at = _now()
    action.updated_at = _now()
    await db.commit()
    await db.refresh(action)
    return _to_out(action)


async def dismiss_action(db: AsyncSession, user: CurrentUser, action_id: UUID) -> ActionOut:
    action = await _get_owned(db, user, action_id)
    _ensure_transition(action, "dismissed")
    action.status = "dismissed"
    action.updated_at = _now()
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
    if action.status in ("dismissed", "completed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot set a reminder on a {action.status} action.",
        )
    label = (payload.reminder or "").strip()
    days = REMINDER_DAYS.get(label)
    if days is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a valid reminder option.")

    # Creating a reminder confirms the action when it is still only suggested.
    if action.status == "suggested":
        _mark_confirmed(action, user)

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
    action.updated_at = _now()
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
