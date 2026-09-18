from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.security import create_access_token, hash_password, verify_password
from ...models.user import User, UserProfile, Workspace
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut, WorkspaceOut


def _display_name(email: str, name: str | None) -> str:
    if name and name.strip():
        return name.strip()
    return email.split("@", 1)[0]


def _to_auth_response(user: User, workspace: Workspace, token: str) -> AuthResponse:
    name = user.profile.display_name if user.profile and user.profile.display_name else str(user.email)
    return AuthResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            email=str(user.email),
            name=name,
            workspace=WorkspaceOut(id=workspace.id, name=workspace.name),
        ),
    )


async def _load_user_graph(db: AsyncSession, user_id) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def register(db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
    user = User(
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    display = _display_name(str(user.email), payload.name)
    db.add(UserProfile(user_id=user.id, display_name=display))
    workspace = Workspace(name=f"{display}'s workspace", owner_user_id=user.id)
    db.add(workspace)
    await db.commit()

    user = await _load_user_graph(db, user.id)
    if user is None or user.workspace is None:
        raise HTTPException(status_code=500, detail="Failed to create workspace.")
    token = create_access_token(user_id=user.id, workspace_id=user.workspace.id)
    return _to_auth_response(user, user.workspace, token)


async def login(db: AsyncSession, payload: LoginRequest) -> AuthResponse:
    result = await db.execute(
        select(User)
        .options(selectinload(User.profile), selectinload(User.workspace))
        .where(User.email == str(payload.email).lower())
    )
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if user.workspace is None:
        display = user.profile.display_name if user.profile and user.profile.display_name else str(user.email)
        user.workspace = Workspace(name=f"{display}'s workspace", owner_user_id=user.id)
        db.add(user.workspace)

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    user = await _load_user_graph(db, user.id)
    if user is None or user.workspace is None:
        raise HTTPException(status_code=500, detail="Workspace is missing.")
    token = create_access_token(user_id=user.id, workspace_id=user.workspace.id)
    return _to_auth_response(user, user.workspace, token)


async def get_me(db: AsyncSession, user_id) -> UserOut:
    user = await _load_user_graph(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.workspace is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace not found.")
    name = user.profile.display_name if user.profile and user.profile.display_name else str(user.email)
    return UserOut(
        id=user.id,
        email=str(user.email),
        name=name,
        workspace=WorkspaceOut(id=user.workspace.id, name=user.workspace.name),
    )


async def update_profile(db: AsyncSession, user_id, name: str) -> UserOut:
    display_name = name.strip()
    if not display_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be blank.")

    user = await _load_user_graph(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.workspace is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Workspace not found.")

    if user.profile is None:
        user.profile = UserProfile(user_id=user.id, display_name=display_name)
    else:
        user.profile.display_name = display_name
    await db.commit()
    await db.refresh(user.profile)
    return UserOut(
        id=user.id,
        email=str(user.email),
        name=display_name,
        workspace=WorkspaceOut(id=user.workspace.id, name=user.workspace.name),
    )
