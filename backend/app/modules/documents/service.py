import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...models.documents import Document
from ..auth.deps import CurrentUser
from .schemas import DocumentOut, UploadResponse
from .validation import detect_mime, safe_filename, validate_extension, validate_file_type

CHUNK_SIZE = 1024 * 1024


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        original_filename=document.original_filename or "document",
        document_type=document.document_type,
        processing_status=document.processing_status or "uploaded",
        created_at=document.created_at,
    )


async def list_documents(db: AsyncSession, user: CurrentUser) -> list[DocumentOut]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == user.workspace_id)
        .order_by(Document.created_at.desc())
    )
    return [_to_out(row) for row in result.scalars().all()]


async def get_document(db: AsyncSession, user: CurrentUser, document_id: UUID) -> DocumentOut:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return _to_out(document)


async def upload_document(db: AsyncSession, user: CurrentUser, file: UploadFile) -> UploadResponse:
    filename = safe_filename(file.filename)
    try:
        extension = validate_extension(filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

    document_id = uuid4()
    relative_key = f"workspaces/{user.workspace_id}/documents/{document_id}/original{extension}"
    dest = Path(settings.upload_dir) / relative_key
    dest.parent.mkdir(parents=True, exist_ok=True)

    sha256 = hashlib.sha256()
    total_size = 0
    first_bytes = b""

    try:
        with dest.open("wb") as handle:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > settings.max_upload_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File must be 20 MB or smaller.")
                if len(first_bytes) < 16:
                    first_bytes += chunk[:16]
                sha256.update(chunk)
                handle.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    except Exception:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read the file.") from None

    if total_size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    detected_mime = detect_mime(first_bytes)
    try:
        validate_file_type(extension, detected_mime)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

    digest = sha256.hexdigest()
    existing = await db.execute(
        select(Document.id).where(
            Document.workspace_id == user.workspace_id,
            Document.sha256 == digest,
        )
    )
    if existing.scalar_one_or_none() is not None:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This document appears to have already been uploaded.")

    document = Document(
        id=document_id,
        workspace_id=user.workspace_id,
        uploaded_by=user.id,
        original_filename=filename,
        extension=extension,
        declared_mime=file.content_type,
        detected_mime=detected_mime,
        file_size=total_size,
        sha256=digest,
        storage_key=relative_key.replace("\\", "/"),
        scan_status="pending",
        processing_status="uploaded",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    return UploadResponse(
        id=document.id,
        status=document.processing_status or "uploaded",
        original_filename=filename,
    )
