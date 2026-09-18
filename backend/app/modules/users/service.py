from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.user import User
from .schemas import UserListItem, UserProfileOut, WorkspaceOut


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


async def list_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
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


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> UserListItem:
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
    return _to_user_item(user)
