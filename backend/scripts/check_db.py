import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text
from app.db import engine


async def main():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("DB check result:", result.scalar())


if __name__ == "__main__":
    asyncio.run(main())
