from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ...db import get_db
from ..auth.deps import CurrentUser, get_current_user
from .schemas import DocumentOut, UploadResponse
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


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.upload_document(db, user, file)
