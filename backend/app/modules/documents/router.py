from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from ...db import get_db
from ..auth.deps import CurrentUser, get_current_user
from .schemas import DocumentOut, ExtractionOut, ExtractionUpdate, PurposeDecisionIn, UploadResponse
from . import service

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_documents(db, user)


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_document(db, user, document_id)


@router.get("/documents/{document_id}/extraction", response_model=ExtractionOut)
async def get_extraction(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_extraction(db, user, document_id)


@router.patch("/documents/{document_id}/extraction", response_model=ExtractionOut)
async def update_extraction(
    document_id: UUID,
    payload: ExtractionUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_extraction(db, user, document_id, payload)


@router.post("/documents/{document_id}/purpose", response_model=ExtractionOut)
async def decide_purpose(
    document_id: UUID,
    payload: PurposeDecisionIn,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.decide_purpose(db, user, document_id, payload.decision)


@router.get("/documents/{document_id}/file")
async def download_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path, media_type, filename, is_temp = await service.get_file_path(db, user, document_id)
    background = BackgroundTask(path.unlink, missing_ok=True) if is_temp else None
    return FileResponse(path, media_type=media_type, filename=filename, background=background)


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_document(db, user, document_id)


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.upload_document(
        db,
        user,
        file,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/documents/{document_id}/decrypt")
async def decrypt_document(
    document_id: UUID,
    payload: dict,
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Attempt to decrypt a previously uploaded password-protected PDF.

    Expects JSON: { "password": "..." }
    """
    password = payload.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")
    result = await service.attempt_decrypt_and_process(db, user, document_id, password)
    # normalize response to include id and status
    return {"id": str(document_id), "status": result.get("status") if isinstance(result, dict) else "queued"}
