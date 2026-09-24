import asyncio
from sqlalchemy import text
from app.db import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("select id, email, otp_type, expires_at, attempt_count, used_at, created_at from auth_otp_codes order by created_at desc limit 20"))
        rows = res.fetchall()
        for r in rows:
            print(r)

if __name__ == '__main__':
    asyncio.run(check())
