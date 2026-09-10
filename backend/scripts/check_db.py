import asyncio
from app.db import engine


async def main():
    async with engine.begin() as conn:
        result = await conn.execute("SELECT 1")
        print("DB check result:", result.scalar())


if __name__ == "__main__":
    asyncio.run(main())
