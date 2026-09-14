from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ..auth.deps import CurrentUser, get_current_user
from .schemas import ActionOut, ReminderCreate
from . import service

router = APIRouter(tags=["actions"])


@router.get("/actions", response_model=list[ActionOut])
async def list_actions(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_actions(db, user)


@router.post("/actions/{action_id}/dismiss", response_model=ActionOut)
async def dismiss_action(
    action_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.dismiss_action(db, user, action_id)


@router.post("/actions/{action_id}/reminders", response_model=ActionOut)
async def create_reminder(
    action_id: UUID,
    payload: ReminderCreate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_reminder(db, user, action_id, payload)
