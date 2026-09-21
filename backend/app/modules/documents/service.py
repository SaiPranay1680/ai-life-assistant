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
from .extract import (
    DOCUMENT_TYPES,
    FieldHit,
    build_structured_payload,
    display_document_type,
    empty_field,
    guess_fields,
    normalize_amount,
    normalize_date,
    normalize_document_type,
    read_document_pages,
    schema_document_type,
)
from .schemas import DocumentOut, ExtractionOut, ExtractionUpdate, UploadResponse
from .validation import detect_mime, safe_filename, validate_extension, validate_extraction, validate_file_type

# Prefer these ExtractionField names when resolving list/detail important dates.
_IMPORTANT_DATE_FIELDS = (
    "expiryDate",
    "due_date",
    "expiry_date",
    "warranty_expiry",
    "warranty_end",
    "billing_period_end",
    "document_date",
    "transaction_date",
)

CHUNK_SIZE = 1024 * 1024

# Left-panel preview safety caps (normal documents are far smaller).
_PREVIEW_MAX_LINES = 500
_PREVIEW_MAX_CHARS = 50_000


def build_preview_lines(text: str) -> list[str]:
    """
    Build the left-panel document preview from full OCR/parsed text.

    Historically this was hard-capped at 8 lines, which truncated insurance and
    other multi-field documents in the review UI.
    """
    preview_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(preview_lines) > _PREVIEW_MAX_LINES:
        preview_lines = preview_lines[:_PREVIEW_MAX_LINES]
    preview_text = "\n".join(preview_lines)
    if len(preview_text) > _PREVIEW_MAX_CHARS:
        preview_text = preview_text[:_PREVIEW_MAX_CHARS]
        preview_lines = [line for line in preview_text.splitlines() if line]
    return preview_lines


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
                ExtractionField.field_name.in_(_IMPORTANT_DATE_FIELDS),
            )
        )
        priority = {name: index for index, name in enumerate(_IMPORTANT_DATE_FIELDS)}
        best: dict = {}
        for row in fields.scalars().all():
            value = row.raw_value or row.normalized_value
            if not value:
                continue
            current = best.get(row.document_id)
            rank = priority.get(row.field_name, 99)
            if current is None or rank < current[0]:
                best[row.document_id] = (rank, value)
        dates = {doc_id: pair[1] for doc_id, pair in best.items()}
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
            ExtractionField.field_name.in_(_IMPORTANT_DATE_FIELDS),
        )
    )
    important_date = None
    priority = {name: index for index, name in enumerate(_IMPORTANT_DATE_FIELDS)}
    best_rank = 99
    for field in date_row.scalars().all():
        value = field.raw_value or field.normalized_value
        if not value:
            continue
        rank = priority.get(field.field_name, 99)
        if rank < best_rank:
            best_rank = rank
            important_date = value
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
        document.document_type = "generic"
        failed_fields = {
            "documentType": FieldHit("generic", "generic", 0.2, "", 1),
            "provider": empty_field(),
            "policyNumber": empty_field(),
            "startDate": empty_field(),
            "expiryDate": empty_field(),
            "premium": empty_field(),
            "preview": FieldHit("Could not read text from this file.", "", 0.2, "", 1),
        }
        await _replace_fields(db, document, failed_fields)
        await db.commit()
        return

    fields = guess_fields(pages)
    doc_type = normalize_document_type(fields["documentType"].raw)
    document.document_type = doc_type
    fields["documentType"] = FieldHit(doc_type, doc_type, fields["documentType"].confidence, "", 1)

    structured_payload = build_structured_payload(doc_type, fields)
    try:
        validated = validate_extraction(doc_type, structured_payload)
        # Keep validated shape available for persistence of complex nulls if needed later.
        _ = validated
    except ValueError:
        # Validation failure should not invent data; mark failed and keep whatever we have.
        document.processing_status = "failed"
        await _replace_fields(db, document, fields)
        await db.commit()
        return

    document.processing_status = "ready_for_review"
    preview_lines = [line.strip() for line in text.splitlines() if line.strip()][:20]
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


async def _rows_to_field_hits(rows: list) -> dict[str, FieldHit]:
    hits: dict[str, FieldHit] = {}
    for row in rows:
        hits[row.field_name] = FieldHit(
            row.raw_value or "",
            row.normalized_value or "",
            float(row.confidence) if row.confidence is not None else 0.0,
            row.evidence_snippet or "",
            row.page_number or 1,
        )
    return hits


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
    field_rows = list(rows.scalars().all())
    values = _field_map(field_rows)
    preview = values.get("preview", "")
    preview_lines = [line for line in preview.splitlines() if line] or ["No text extracted yet."]

    raw_type = values.get("documentType") or document.document_type or "generic"
    type_id = normalize_document_type(raw_type)
    # Frontend review form still shows familiar labels for the document type dropdown.
    display_type = display_document_type(type_id)

    structured = None
    try:
        hits = await _rows_to_field_hits(field_rows)
        if "documentType" not in hits:
            hits["documentType"] = FieldHit(type_id, type_id, 0.5, "", 1)
        payload = build_structured_payload(type_id, hits)
        structured = validate_extraction(type_id, payload).model_dump(mode="json")
    except ValueError:
        structured = None

    # Flat insurance-shaped fields stay for older clients; type-specific docs must not
    # leak into policyNumber / startDate / expiryDate / premium.
    if type_id in ("utility_bill", "purchase_receipt", "warranty"):
        flat_provider = ""
        if type_id == "utility_bill":
            flat_provider = values.get("provider") or ""
            if structured and isinstance(structured.get("provider"), dict):
                flat_provider = (
                    structured["provider"].get("raw")
                    or structured["provider"].get("normalized")
                    or flat_provider
                )
        elif type_id == "purchase_receipt" and structured and isinstance(structured.get("merchant"), dict):
            flat_provider = (
                structured["merchant"].get("raw")
                or structured["merchant"].get("normalized")
                or ""
            )
        elif type_id == "warranty" and structured and isinstance(structured.get("warranty_provider"), dict):
            flat_provider = (
                structured["warranty_provider"].get("raw")
                or structured["warranty_provider"].get("normalized")
                or ""
            )
        return ExtractionOut(
            documentType=display_type,
            provider=flat_provider,
            policyNumber="",
            startDate="",
            expiryDate="",
            premium="",
            previewTitle=document.original_filename or "Document",
            previewLines=preview_lines,
            processingStatus=document.processing_status or "uploaded",
            structuredExtraction=structured,
        )

    return ExtractionOut(
        documentType=display_type,
        provider=values.get("provider") or "",
        policyNumber=values.get("policyNumber") or "",
        startDate=values.get("startDate") or "",
        expiryDate=values.get("expiryDate") or "",
        premium=values.get("premium") or "",
        previewTitle=document.original_filename or "Document",
        previewLines=preview_lines,
        processingStatus=document.processing_status or "uploaded",
        structuredExtraction=structured,
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

    doc_type_input = payload.documentType.strip()
    if doc_type_input not in DOCUMENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a valid document type.")
    type_id = normalize_document_type(doc_type_input)

    structured_edits = {k: (v or "").strip() for k, v in (payload.structuredFields or {}).items()}

    start = payload.startDate.strip()
    expiry = payload.expiryDate.strip()
    # Type-specific docs use their own date fields, not insurance slots.
    if type_id not in ("utility_bill", "purchase_receipt", "warranty"):
        if start and not normalize_date(start):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid start date.")
        if expiry and not normalize_date(expiry):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid expiry date.")
    elif type_id == "utility_bill":
        for date_key in ("billing_period_start", "billing_period_end", "due_date"):
            raw_date = structured_edits.get(date_key, "")
            if raw_date and not normalize_date(raw_date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Enter a valid {date_key.replace('_', ' ')}.",
                )
    elif type_id == "purchase_receipt":
        for date_key in ("purchase_date", "transaction_date"):
            raw_date = structured_edits.get(date_key, "")
            if raw_date and not normalize_date(raw_date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Enter a valid {date_key.replace('_', ' ')}.",
                )
    else:
        for date_key in ("purchase_date", "warranty_start", "warranty_expiry"):
            raw_date = structured_edits.get(date_key, "")
            if raw_date and not normalize_date(raw_date):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Enter a valid {date_key.replace('_', ' ')}.",
                )

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
        return FieldHit(raw, normalized, 1.0 if raw else 0.0, evidence, page)

    def norm_for(name: str, raw: str) -> str:
        if name.endswith("_date") or name.endswith("_start") or name.endswith("_end") or name.endswith("_expiry") or name in {
            "startDate",
            "expiryDate",
            "transaction_date",
            "purchase_date",
            "document_date",
            "effective_date",
            "due_date",
            "warranty_start",
            "warranty_expiry",
        }:
            return normalize_date(raw) if raw else ""
        if name in {"premium", "amount_due", "total", "subtotal", "tax", "discount", "previous_balance", "current_charges"}:
            return normalize_amount(raw) if raw else ""
        return raw

    provider = (structured_edits.get("provider") or payload.provider).strip()
    fields: dict[str, FieldHit] = {
        "documentType": kept("documentType", type_id, type_id),
        "provider": kept("provider", provider, provider),
    }

    if type_id == "utility_bill":
        # Persist only type-specific utility fields — never invent policyNumber/premium aliases.
        utility_keys = (
            "bill_number",
            "customer_id",
            "account_number",
            "billing_period_start",
            "billing_period_end",
            "due_date",
            "amount_due",
            "service_address",
            "previous_balance",
            "current_charges",
            "currency",
        )
        for key in utility_keys:
            if key in structured_edits:
                raw = structured_edits[key]
            elif key in by_name:
                raw = by_name[key].raw_value or by_name[key].normalized_value or ""
            else:
                raw = ""
            fields[key] = kept(key, raw, norm_for(key, raw))
    elif type_id == "purchase_receipt":
        merchant = (structured_edits.get("merchant") or payload.provider).strip()
        fields["merchant"] = kept("merchant", merchant, merchant)
        # Drop unused provider alias for receipts.
        fields.pop("provider", None)
        purchase_keys = (
            "receipt_number",
            "purchase_date",
            "transaction_date",
            "subtotal",
            "tax",
            "discount",
            "total",
            "payment_method",
            "currency",
        )
        for key in purchase_keys:
            if key in structured_edits:
                raw = structured_edits[key]
            elif key in by_name:
                raw = by_name[key].raw_value or by_name[key].normalized_value or ""
            else:
                raw = ""
            fields[key] = kept(key, raw, norm_for(key, raw))
        # Preserve parsed items JSON unless the client overwrites it.
        if "items" in by_name and "items" not in structured_edits:
            row = by_name["items"]
            fields["items"] = FieldHit(
                row.raw_value or "",
                row.normalized_value or "",
                float(row.confidence or 0.0),
                row.evidence_snippet or "",
                row.page_number or 1,
            )
        elif "items" in structured_edits:
            raw = structured_edits["items"]
            fields["items"] = kept("items", raw, raw)
    elif type_id == "warranty":
        fields.pop("provider", None)
        warranty_keys = (
            "product",
            "brand",
            "model",
            "serial_number",
            "warranty_provider",
            "purchase_date",
            "warranty_start",
            "warranty_expiry",
            "warranty_duration",
        )
        for key in warranty_keys:
            if key in structured_edits:
                raw = structured_edits[key]
            elif key in by_name:
                raw = by_name[key].raw_value or by_name[key].normalized_value or ""
            else:
                raw = ""
            fields[key] = kept(key, raw, norm_for(key, raw))
    else:
        policy = payload.policyNumber.strip()
        premium = payload.premium.strip()
        fields["policyNumber"] = kept("policyNumber", policy, policy)
        fields["startDate"] = kept("startDate", start, normalize_date(start) if start else "")
        fields["expiryDate"] = kept("expiryDate", expiry, normalize_date(expiry) if expiry else "")
        fields["premium"] = kept("premium", premium, normalize_amount(premium) if premium else "")

        type_mirrors = {
            "insurance": {
                "provider": "provider",
                "policy_number": "policyNumber",
                "effective_date": "startDate",
                "expiry_date": "expiryDate",
                "premium": "premium",
            },
            "generic": {
                "provider": "provider",
                "document_date": "startDate",
            },
        }
        mirror_key = schema_document_type(type_id)
        for typed_name, legacy_name in type_mirrors.get(mirror_key, {}).items():
            source = fields[legacy_name]
            fields[typed_name] = FieldHit(
                source.raw,
                source.normalized,
                source.confidence,
                source.evidence,
                source.page,
            )
        for key, raw in structured_edits.items():
            if key in fields:
                continue
            fields[key] = kept(key, raw, norm_for(key, raw))

    preview_row = by_name.get("preview")
    if preview_row:
        fields["preview"] = FieldHit(
            preview_row.raw_value or "",
            preview_row.normalized_value or "",
            float(preview_row.confidence or 0.8),
            preview_row.evidence_snippet or "",
            preview_row.page_number or 1,
        )

    try:
        validate_extraction(type_id, build_structured_payload(type_id, fields))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await _replace_fields(db, document, fields)
    document.document_type = type_id
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
