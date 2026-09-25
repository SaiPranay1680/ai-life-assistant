from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ..auth.deps import get_current_user, CurrentUser
from . import service

router = APIRouter(tags=["privacy"], prefix="/privacy")


@router.post("/delete")
async def delete_account(user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete the current user's account and all associated data."""
    return await service.delete_account(db=db, current_user=user)
