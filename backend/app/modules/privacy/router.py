from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ..auth.deps import CurrentUser, get_current_user
from .service import export_workspace_data

router = APIRouter(tags=["privacy"])


@router.get("/privacy/export")
async def export_data(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the caller's workspace metadata as JSON.

    Original file bytes and password hashes are deliberately excluded. Document
    metadata and reviewed extraction fields remain available for portability.
    """
    content = await export_workspace_data(db, user)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="ai-life-assistant-export.json"'},
    )
