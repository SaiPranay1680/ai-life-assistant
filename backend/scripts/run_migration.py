import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


async def run():
    dsn = os.getenv("DATABASE_URL") or "postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant"
    dsn = dsn.replace("+asyncpg", "")
    migrations_dir = BACKEND_DIR / "migrations"
    # initial.sql must run first. glob+sorted would apply 002-006 before
    # initial.sql, which breaks a fresh database (workspaces before users).
    initial = migrations_dir / "initial.sql"
    numbered = sorted(p for p in migrations_dir.glob("*.sql") if p.name != "initial.sql")
    files = ([initial] if initial.exists() else []) + numbered
    print("Using DSN:", dsn)
    conn = await asyncpg.connect(dsn)
    try:
        for sql_path in files:
            print("Applying", sql_path.name)
            sql = sql_path.read_text(encoding="utf-8")
            chunks = [sql] if "$$" in sql else [part.strip() for part in sql.split(";") if part.strip()]
            for stmt in chunks:
                await conn.execute(stmt)
        print("Migration applied successfully")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
