from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.security import hash_password
from ...models.actions import Action
from ...models.documents import Document
from ...models.reminder import Reminder
from ...models.user import User, UserProfile, Workspace
from ..users.schemas import UserListItem, UserProfileOut, WorkspaceOut
from .schemas import (
    AdminActionItem,
    AdminDocumentItem,
    AdminUserUpdate,
    DatabaseTableStats,
    SystemStatsOut,
)


def _to_user_item(user: User) -> UserListItem:
    name = getattr(user, "name", None)
    if not name and user.profile:
        name = user.profile.display_name or (
            f"{user.profile.first_name or ''} {user.profile.last_name or ''}".strip() or None
        )
    if not name:
        name = str(user.email).split("@", 1)[0]

    profile_data = None
    if user.profile:
        profile_data = UserProfileOut(
            first_name=user.profile.first_name,
            last_name=user.profile.last_name,
            display_name=user.profile.display_name,
            avatar_url=user.profile.avatar_url,
            locale=user.profile.locale,
            timezone=user.profile.timezone,
        )

    workspace_data = None
    if user.workspace:
        workspace_data = WorkspaceOut(
            id=user.workspace.id,
            name=user.workspace.name,
        )

    return UserListItem(
        id=user.id,
        email=str(user.email),
        name=name,
        role=getattr(user, "role", "user") or "user",
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        profile=profile_data,
        workspace=workspace_data,
    )


async def get_system_stats(db: AsyncSession) -> SystemStatsOut:
    # 1. Users metrics
    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active.is_(True))) or 0
    admin_users = await db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
    regular_users = total_users - admin_users

    # 2. Documents metrics
    total_docs = await db.scalar(select(func.count(Document.id))) or 0

    doc_types_rows = (await db.execute(
        select(Document.document_type, func.count(Document.id)).group_by(Document.document_type)
    )).all()
    docs_by_type = {row[0] or "Unclassified": row[1] for row in doc_types_rows}

    doc_status_rows = (await db.execute(
        select(Document.processing_status, func.count(Document.id)).group_by(Document.processing_status)
    )).all()
    docs_by_status = {row[0] or "Unknown": row[1] for row in doc_status_rows}

    # 3. Actions metrics
    total_actions = await db.scalar(select(func.count(Action.id))) or 0

    action_status_rows = (await db.execute(
        select(Action.status, func.count(Action.id)).group_by(Action.status)
    )).all()
    actions_by_status = {row[0] or "Unknown": row[1] for row in action_status_rows}

    action_prio_rows = (await db.execute(
        select(Action.priority, func.count(Action.id)).group_by(Action.priority)
    )).all()
    actions_by_priority = {row[0] or "medium": row[1] for row in action_prio_rows}

    # 4. Reminders metrics
    total_reminders = await db.scalar(select(func.count(Reminder.id))) or 0

    # 5. Database tables overview
    tables = await get_database_tables(db)

    return SystemStatsOut(
        database_connected=True,
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        regular_users=regular_users,
        total_documents=total_docs,
        documents_by_type=docs_by_type,
        documents_by_status=docs_by_status,
        total_actions=total_actions,
        actions_by_status=actions_by_status,
        actions_by_priority=actions_by_priority,
        total_reminders=total_reminders,
        tables=tables,
    )


async def get_database_tables(db: AsyncSession) -> list[DatabaseTableStats]:
    # Query postgres stats for table names, estimated row counts, and sizes
    stmt = text("""
        SELECT 
            relname AS table_name,
            COALESCE(n_live_tup, 0) AS row_count,
            pg_size_pretty(pg_total_relation_size(relid)) AS total_size
        FROM pg_stat_user_tables
        ORDER BY relname;
    """)
    result = await db.execute(stmt)
    rows = result.fetchall()
    
    tables: list[DatabaseTableStats] = []
    # Key application tables to always ensure exact live counts for
    tracked_tables = [
        "users", "user_profiles", "workspaces", "documents", 
        "extractions", "actions", "reminders", "audit_logs"
    ]
    
    table_map = {r[0]: DatabaseTableStats(table_name=r[0], row_count=int(r[1]), total_size=str(r[2])) for r in rows}
    
    for t_name in tracked_tables:
        if t_name in table_map:
            # Count exact rows
            try:
                exact_count = await db.scalar(text(f'SELECT count(*) FROM "{t_name}"'))
                if exact_count is not None:
                    table_map[t_name].row_count = int(exact_count)
            except Exception:
                pass
        else:
            try:
                exact_count = await db.scalar(text(f'SELECT count(*) FROM "{t_name}"'))
                size_res = await db.scalar(text(f"SELECT pg_size_pretty(pg_total_relation_size('\"{t_name}\"'))"))
                table_map[t_name] = DatabaseTableStats(
                    table_name=t_name,
                    row_count=int(exact_count or 0),
                    total_size=str(size_res or "0 bytes"),
                )
            except Exception:
                pass

    return sorted(table_map.values(), key=lambda x: x.table_name)


async def list_admin_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 200,
) -> list[UserListItem]:
    stmt = (
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [_to_user_item(u) for u in users]


async def update_user_fields(
    db: AsyncSession,
    user_id: UUID,
    payload: AdminUserUpdate,
) -> UserListItem:
    stmt = (
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    if payload.email is not None:
        user.email = str(payload.email).lower()

    if payload.name is not None:
        user.name = payload.name.strip()
        if user.profile:
            user.profile.display_name = payload.name.strip()
        else:
            user.profile = UserProfile(user_id=user.id, display_name=payload.name.strip())

    if payload.role is not None:
        user.role = payload.role

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.email_verified is not None:
        user.email_verified = payload.email_verified

    if payload.password is not None and payload.password.strip():
        user.password_hash = hash_password(payload.password.strip())

    user.updated_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    return _to_user_item(user)


async def delete_user(
    db: AsyncSession,
    user_id: UUID,
    current_admin_id: UUID,
) -> dict:
    if user_id == current_admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account.",
        )

    stmt = select(User).options(selectinload(User.profile), selectinload(User.workspace)).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    if user.profile is not None:
        await db.delete(user.profile)
    if user.workspace is not None:
        await db.delete(user.workspace)

    await db.delete(user)
    await db.commit()
    return {"message": f"User '{user_id}' and all associated workspace data have been deleted successfully."}


async def list_all_documents(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 200,
) -> list[AdminDocumentItem]:
    stmt = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        AdminDocumentItem(
            id=d.id,
            workspace_id=d.workspace_id,
            uploaded_by=d.uploaded_by,
            file_name=d.original_filename or "untitled",
            mime_type=d.detected_mime or d.declared_mime or "application/octet-stream",
            file_size_bytes=d.file_size or 0,
            document_type=d.document_type or "Unclassified",
            document_status=d.processing_status or "uploaded",
            created_at=d.created_at,
        )
        for d in docs
    ]


async def list_all_actions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 200,
) -> list[AdminActionItem]:
    stmt = (
        select(Action)
        .order_by(Action.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()
    return [
        AdminActionItem(
            id=a.id,
            workspace_id=a.workspace_id,
            document_id=a.source_document_id,
            title=a.title,
            action_type=a.action_type,
            status=a.status,
            priority=a.priority,
            due_date=str(a.due_at) if a.due_at else None,
            created_at=a.created_at,
        )
        for a in actions
    ]
