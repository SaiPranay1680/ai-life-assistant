import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_delete_account_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/privacy/delete")
        assert resp.status_code == 401
