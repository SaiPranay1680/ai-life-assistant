import asyncio
import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...models.audit import record_audit
from ...models.documents import Document
from ...models.extraction import ExtractionField
from ...security.scanner import ScannerUnavailable, get_scanner
from ...storage.factory import get_storage
from ..auth.deps import CurrentUser
from .extract import DOCUMENT_TYPES, FieldHit, empty_field, guess_fields, normalize_amount, normalize_date, read_document_pages
from .schemas import DocumentOut, ExtractionOut, ExtractionUpdate, UploadResponse
from .validation import detect_mime, safe_filename, validate_extension, validate_file_type

CHUNK_SIZE = 1024 * 1024


def _to_out(document: Document, important_date: str | None = None) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        original_filename=document.original_filename or "document",
        document_type=document.document_type,
        processing_status=document.processing_status or "uploaded",
        important_date=important_date,
        created_at=document.created_at,
    )


async def list_documents(db: AsyncSession, user: CurrentUser) -> list[DocumentOut]:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == user.workspace_id)
        .order_by(Document.created_at.desc())
    )
    documents = list(result.scalars().all())
    ids = [row.id for row in documents]
    dates: dict = {}
    if ids:
        fields = await db.execute(
            select(ExtractionField).where(
                ExtractionField.document_id.in_(ids),
                ExtractionField.workspace_id == user.workspace_id,
                ExtractionField.field_name == "expiryDate",
            )
        )
        for row in fields.scalars().all():
            dates[row.document_id] = row.raw_value or row.normalized_value
    return [_to_out(row, dates.get(row.id)) for row in documents]


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
    date_row = await db.execute(
        select(ExtractionField).where(
            ExtractionField.document_id == document.id,
            ExtractionField.workspace_id == user.workspace_id,
            ExtractionField.field_name == "expiryDate",
        )
    )
    field = date_row.scalar_one_or_none()
    important_date = (field.raw_value or field.normalized_value) if field else None
    return _to_out(document, important_date)


async def upload_document(
    db: AsyncSession,
    user: CurrentUser,
    file: UploadFile,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> UploadResponse:
    filename = safe_filename(file.filename)
    try:
        extension = validate_extension(filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

    storage = get_storage()
    try:
        await storage.cleanup_orphans(settings.quarantine_ttl_seconds)
    except Exception:
        pass

    document_id = uuid4()
    relative_key = f"workspaces/{user.workspace_id}/documents/{document_id}/original{extension}"
    sha256 = hashlib.sha256()
    total_size = 0
    first_bytes = b""

    async def chunks():
        nonlocal total_size, first_bytes
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > settings.max_upload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File must be 20 MB or smaller.",
                )
            if len(first_bytes) < 16:
                first_bytes += chunk[:16]
            sha256.update(chunk)
            yield chunk

    async def reject_quarantine() -> None:
        await storage.delete_quarantine(relative_key)

    try:
        await storage.save_quarantine(relative_key, chunks())
    except HTTPException:
        await reject_quarantine()
        raise
    except Exception:
        await reject_quarantine()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not read the file.") from None

    if total_size == 0:
        await reject_quarantine()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    detected_mime = detect_mime(first_bytes)
    try:
        validate_file_type(extension, detected_mime)
    except ValueError as exc:
        await reject_quarantine()
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc

    digest = sha256.hexdigest()
    existing = await db.execute(
        select(Document.id).where(
            Document.workspace_id == user.workspace_id,
            Document.sha256 == digest,
        )
    )
    if existing.scalar_one_or_none() is not None:
        await reject_quarantine()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document appears to have already been uploaded.",
        )

    audit_meta = {
        "workspace_id": str(user.workspace_id),
        "document_id": str(document_id),
        "sha256": digest,
        "original_filename": filename,
    }
    try:
        async with storage.open_for_read(relative_key, location="quarantine") as quarantine_path:
            scan_result = await get_scanner().scan(quarantine_path)
    except ScannerUnavailable:
        await reject_quarantine()
        await record_audit(
            db,
            user_id=user.id,
            event="UPLOAD_REJECTED_SCANNER_UNAVAILABLE",
            metadata=audit_meta,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File security scanning is temporarily unavailable.",
        ) from None
    except Exception:
        await reject_quarantine()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file failed the security scan.") from None

    if not scan_result.clean:
        await reject_quarantine()
        await record_audit(
            db,
            user_id=user.id,
            event="MALWARE_REJECTED",
            metadata={**audit_meta, "threat_name": scan_result.threat_name, "scan_source": scan_result.source},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This file failed the security scan.")

    try:
        await storage.promote(relative_key)
    except Exception:
        await reject_quarantine()
        await storage.delete_permanent(relative_key)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not store the file.") from None

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
        scan_status="clean",
        processing_status="queued",
    )
    db.add(document)
    try:
        await db.commit()
        await db.refresh(document)
    except Exception:
        await storage.delete_permanent(relative_key)
        raise

    from ...worker.tasks import process_document_task

    try:
        process_document_task.delay(str(document.id))
    except Exception:
        document.processing_status = "failed"
        await db.commit()
        await db.refresh(document)

    return UploadResponse(
        id=document.id,
        status=document.processing_status or "queued",
        original_filename=filename,
    )


def _field_map(rows: list[ExtractionField]) -> dict[str, str]:
    return {row.field_name: (row.raw_value or row.normalized_value or "") for row in rows}


async def process_document_pipeline(db: AsyncSession, document: Document) -> None:
    document.processing_status = "processing"
    await db.commit()

    if (document.scan_status or "") != "clean" or not document.storage_key:
        document.processing_status = "failed"
        await db.commit()
        return

    storage = get_storage()
    if not await storage.exists_permanent(document.storage_key):
        document.processing_status = "failed"
        await db.commit()
        return

    extension = (document.extension or "").lower()
    is_pdf = extension == ".pdf" or (document.detected_mime == "application/pdf")

    pages: list[tuple[int, str]] = []
    try:
        async with storage.open_for_read(document.storage_key, location="permanent") as path:
            pages = await asyncio.to_thread(read_document_pages, path, is_pdf)
    except Exception:
        document.processing_status = "failed"
        await db.commit()
        return

    text = "\n".join(part for _, part in pages)

    if len(text.strip()) < 8:
        document.processing_status = "failed"
        document.document_type = "Important document"
        await _replace_fields(
            db,
            document,
            {
                "documentType": FieldHit("Important document", "Important document", 0.2, "", 1),
                "provider": empty_field(),
                "policyNumber": empty_field(),
                "startDate": empty_field(),
                "expiryDate": empty_field(),
                "premium": empty_field(),
                "preview": FieldHit("Could not read text from this file.", "", 0.2, "", 1),
            },
        )
        await db.commit()
        return

    fields = guess_fields(pages)
    document.document_type = fields["documentType"].raw
    document.processing_status = "ready_for_review"
    preview_lines = [line.strip() for line in text.splitlines() if line.strip()][:8]
    fields["preview"] = FieldHit(
        "\n".join(preview_lines),
        "",
        0.8,
        preview_lines[0] if preview_lines else "",
        pages[0][0] if pages else 1,
    )
    await _replace_fields(db, document, fields)
    await db.commit()


async def _replace_fields(
    db: AsyncSession,
    document: Document,
    fields: dict[str, FieldHit],
) -> None:
    existing = await db.execute(
        select(ExtractionField).where(ExtractionField.document_id == document.id)
    )
    for row in existing.scalars().all():
        await db.delete(row)
    await db.flush()
    for name, hit in fields.items():
        db.add(
            ExtractionField(
                document_id=document.id,
                workspace_id=document.workspace_id,
                field_name=name,
                raw_value=hit.raw,
                normalized_value=hit.normalized,
                confidence=hit.confidence,
                page_number=hit.page,
                evidence_snippet=(hit.evidence or "")[:200],
            )
        )


async def get_extraction(db: AsyncSession, user: CurrentUser, document_id: UUID) -> ExtractionOut:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    rows = await db.execute(
        select(ExtractionField).where(
            ExtractionField.document_id == document.id,
            ExtractionField.workspace_id == user.workspace_id,
        )
    )
    values = _field_map(list(rows.scalars().all()))
    preview = values.get("preview", "")
    preview_lines = [line for line in preview.splitlines() if line] or ["No text extracted yet."]
    return ExtractionOut(
        documentType=values.get("documentType") or document.document_type or "Important document",
        provider=values.get("provider") or "",
        policyNumber=values.get("policyNumber") or "",
        startDate=values.get("startDate") or "",
        expiryDate=values.get("expiryDate") or "",
        premium=values.get("premium") or "",
        previewTitle=document.original_filename or "Document",
        previewLines=preview_lines,
        processingStatus=document.processing_status or "uploaded",
    )


async def update_extraction(
    db: AsyncSession,
    user: CurrentUser,
    document_id: UUID,
    payload: ExtractionUpdate,
) -> ExtractionOut:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.processing_status in ("uploaded", "queued", "processing", "ocr_required"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is still processing. Try again when review is ready.",
        )
    if document.processing_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document could not be processed.",
        )

    doc_type = payload.documentType.strip()
    if doc_type not in DOCUMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a valid document type.")

    start = payload.startDate.strip()
    expiry = payload.expiryDate.strip()
    if start and not normalize_date(start):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid start date.")
    if expiry and not normalize_date(expiry):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid expiry date.")

    rows = await db.execute(
        select(ExtractionField).where(
            ExtractionField.document_id == document.id,
            ExtractionField.workspace_id == user.workspace_id,
        )
    )
    by_name = {row.field_name: row for row in rows.scalars().all()}

    def kept(name: str, raw: str, normalized: str) -> FieldHit:
        row = by_name.get(name)
        page = (row.page_number if row else 1) or 1
        evidence = ((row.evidence_snippet if row else raw) or raw)[:200]
        return FieldHit(raw, normalized, 1.0, evidence, page)

    provider = payload.provider.strip()
    policy = payload.policyNumber.strip()
    premium = payload.premium.strip()
    fields = {
        "documentType": kept("documentType", doc_type, doc_type),
        "provider": kept("provider", provider, provider),
        "policyNumber": kept("policyNumber", policy, policy),
        "startDate": kept("startDate", start, normalize_date(start)),
        "expiryDate": kept("expiryDate", expiry, normalize_date(expiry)),
        "premium": kept("premium", premium, normalize_amount(premium)),
    }
    preview_row = by_name.get("preview")
    if preview_row:
        fields["preview"] = FieldHit(
            preview_row.raw_value or "",
            preview_row.normalized_value or "",
            float(preview_row.confidence or 0.8),
            preview_row.evidence_snippet or "",
            preview_row.page_number or 1,
        )
    await _replace_fields(db, document, fields)
    document.document_type = doc_type
    document.processing_status = "reviewed"
    await db.commit()
    return await get_extraction(db, user, document_id)


async def get_file_path(db: AsyncSession, user: CurrentUser, document_id: UUID) -> tuple[Path, str, str, bool]:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None or not document.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    storage = get_storage()
    try:
        path, is_temp = await storage.materialize(document.storage_key, location="permanent")
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.") from None
    filename = document.original_filename or Path(document.storage_key).name
    return path, document.detected_mime or "application/octet-stream", filename, is_temp


async def delete_document(db: AsyncSession, user: CurrentUser, document_id: UUID) -> None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    storage_key = document.storage_key
    await db.delete(document)
    await db.commit()
    if storage_key:
        await get_storage().delete_permanent(storage_key)
