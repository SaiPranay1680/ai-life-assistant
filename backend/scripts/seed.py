import asyncio
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.db import AsyncSessionLocal
from app.models.user import User, UserProfile, Workspace

ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "16271627"
ADMIN_ROLE = "admin"


async def seed_admin():
    print(f"--- Seeding Default Admin Account ---")
    print(f"Email:    {ADMIN_EMAIL}")
    print(f"Username: {ADMIN_NAME}")
    print(f"Password: {ADMIN_PASSWORD}")
    print(f"Role:     {ADMIN_ROLE}")
    
    async with AsyncSessionLocal() as db:
        stmt = (
            select(User)
            .options(selectinload(User.profile), selectinload(User.workspace))
            .where(User.email == ADMIN_EMAIL.lower())
        )
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if user is None:
            user = User(
                email=ADMIN_EMAIL.lower(),
                password_hash=hash_password(ADMIN_PASSWORD),
                name=ADMIN_NAME,
                role=ADMIN_ROLE,
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            await db.flush()

            profile = UserProfile(
                user_id=user.id,
                display_name=ADMIN_NAME,
            )
            db.add(profile)

            workspace = Workspace(
                name=f"{ADMIN_NAME}'s workspace",
                owner_user_id=user.id,
            )
            db.add(workspace)
            await db.commit()
            print(f"-> Successfully created admin account with ID: {user.id}")
        else:
            user.name = ADMIN_NAME
            user.role = ADMIN_ROLE
            user.password_hash = hash_password(ADMIN_PASSWORD)
            user.is_active = True
            user.email_verified = True

            if user.profile is None:
                user.profile = UserProfile(user_id=user.id, display_name=ADMIN_NAME)
                db.add(user.profile)
            else:
                user.profile.display_name = ADMIN_NAME

            if user.workspace is None:
                user.workspace = Workspace(name=f"{ADMIN_NAME}'s workspace", owner_user_id=user.id)
                db.add(user.workspace)

            await db.commit()
            print(f"-> Admin account existed and was successfully updated to role '{ADMIN_ROLE}' (ID: {user.id})")

    print("--- Admin Seeding Completed Successfully ---")


if __name__ == "__main__":
    asyncio.run(seed_admin())
