import os
import asyncio
import asyncpg

async def run():
    dsn = os.getenv("DATABASE_URL") or "postgresql+asyncpg://ai_app:1627@localhost:5432/ai_life_assistant"
    # asyncpg expects a postgresql:// URI without +asyncpg
    dsn = dsn.replace("+asyncpg", "")
    sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations", "initial.sql")
    print("Using DSN:", dsn)
    print("Reading SQL from:", sql_path)
    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn = await asyncpg.connect(dsn)
    try:
        # asyncpg can execute multiple commands in a single execute
        await conn.execute(sql)
        print("Migration applied successfully")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run())
