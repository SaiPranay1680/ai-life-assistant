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
    files = sorted(migrations_dir.glob("*.sql"))
    print("Using DSN:", dsn)
    conn = await asyncpg.connect(dsn)
    try:
        for sql_path in files:
            print("Applying", sql_path.name)
            sql = sql_path.read_text(encoding="utf-8")
            await conn.execute(sql)
        print("Migration applied successfully")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
