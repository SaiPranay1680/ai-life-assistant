#!/bin/sh
set -e

python - <<'PY'
import asyncio
import os
import sys

import asyncpg


async def wait_for_postgres() -> None:
    dsn = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    last_error = None
    for _ in range(60):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print("PostgreSQL is ready")
            return
        except Exception as exc:  # noqa: BLE001 — wait loop
            last_error = exc
            print(f"Waiting for PostgreSQL: {exc}")
            await asyncio.sleep(1)
    print(f"PostgreSQL did not become ready: {last_error}", file=sys.stderr)
    sys.exit(1)


asyncio.run(wait_for_postgres())
PY

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  python scripts/run_migration.py
fi
exec "$@"
