from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from .schemas import UserListItem
from . import service

router = APIRouter(tags=["users"])


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of users to return"),
    db: AsyncSession = Depends(get_db),
):
    """Fetch complete list of users from the database."""
    return await service.list_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a specific user by ID."""
    return await service.get_user_by_id(db, user_id)
