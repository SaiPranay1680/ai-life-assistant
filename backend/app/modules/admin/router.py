from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ..auth.deps import CurrentUser, require_admin
from ..users.schemas import UserListItem
from . import service
from .schemas import (
    AdminActionItem,
    AdminDocumentItem,
    AdminUserUpdate,
    DatabaseTableStats,
    SystemStatsOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats", response_model=SystemStatsOut)
async def get_system_stats(
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Fetch complete system and database metrics."""
    return await service.get_system_stats(db)


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users in the system."""
    return await service.list_admin_users(db, skip=skip, limit=limit)


@router.patch("/users/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to update any field of a user."""
    return await service.update_user_fields(db, user_id=user_id, payload=payload)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to delete a user account and cascade associated data."""
    return await service.delete_user(db, user_id=user_id, current_admin_id=admin.id)


@router.get("/database/tables", response_model=list[DatabaseTableStats])
async def get_database_tables(
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Inspect all database tables, live row counts, and storage sizes."""
    return await service.get_database_tables(db)


@router.get("/documents", response_model=list[AdminDocumentItem])
async def list_all_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """View all documents uploaded across all workspaces."""
    return await service.list_all_documents(db, skip=skip, limit=limit)


@router.get("/actions", response_model=list[AdminActionItem])
async def list_all_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    admin: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """View all actions across all workspaces."""
    return await service.list_all_actions(db, skip=skip, limit=limit)
