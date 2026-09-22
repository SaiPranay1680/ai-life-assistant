import asyncio
import hashlib
import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...models.audit import record_audit
from ...models.documents import Document
from ...models.extraction import ExtractionField
from ...security.scanner import ScannerUnavailable, get_scanner
from ...storage.factory import get_storage
from ..auth.deps import CurrentUser
from ..intelligence.important import (
    META_FIELD_NAMES,
    canonicalize_key,
    hidden_review_keys,
    humanize_label,
    important_keys_for,
)
from ..intelligence.provider import get_provider
from ..intelligence.types import IntelligenceResult, NormalizedDocument, user_facing_reason
from .extract import (
    DOCUMENT_TYPES,
    FieldHit,
    build_structured_payload,
    display_document_type,
    empty_field,
    extract_pdf_pages,
    guess_fields,
    inspect_pdf,
    normalize_document_type,
    ocr_image,
    ocr_pdf_pages,
    read_document_pages,
    schema_document_type,
)
from .folders import (
    FOLDER_CATEGORY_FIELD,
    FOLDER_FIELD_NAMES,
    FOLDER_SUBCATEGORY_FIELD,
    guess_folder,
    normalize_folder,
)
from .text import normalize_amount, normalize_date
from .schemas import DocumentOut, ExtractedFieldOut, ExtractionOut, ExtractionUpdate, UploadResponse
from .validation import detect_mime, safe_filename, validate_extension, validate_extraction, validate_file_type

logger = logging.getLogger(__name__)

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
    "pay_before",
    "policy_expiry_date",
)
_FOLDER_LOOKUP_FIELDS = _IMPORTANT_DATE_FIELDS + FOLDER_FIELD_NAMES
CHUNK_SIZE = 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
# Rejected photos and discarded files are not stored. Hide them from the vault,
# skip them in quota, and allow the same file to be uploaded again later.
_NOT_STORED_STATUSES = ("rejected", "discarded")


async def _assert_workspace_quota(db: AsyncSession, workspace_id: UUID, extra_bytes: int) -> None:
    active = Document.processing_status.notin_(_NOT_STORED_STATUSES)
    count = await db.scalar(
        select(func.count()).select_from(Document).where(Document.workspace_id == workspace_id, active)
    )
    if (count or 0) >= settings.max_workspace_documents:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Document limit reached. Delete unused files and try again.",
        )
    used = await db.scalar(
        select(func.coalesce(func.sum(Document.file_size), 0)).where(Document.workspace_id == workspace_id, active)
    )
    if (used or 0) + extra_bytes > settings.max_workspace_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Storage limit reached. Delete unused files and try again.",
        )

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


def _to_out(
    document: Document,
    important_date: str | None = None,
    folder_category: str | None = None,
    folder_subcategory: str | None = None,
) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        original_filename=document.original_filename or "document",
        document_type=document.document_type,
        processing_status=document.processing_status or "uploaded",
        important_date=important_date,
        purpose_status=document.purpose_status,
        purpose_reason=user_facing_reason(document.purpose_status or "", document.purpose_reason or "") or None,
        purpose_category=document.purpose_category,
        purpose_subtype=document.purpose_subtype,
        folder_category=folder_category,
        folder_subcategory=folder_subcategory,
        page_count=document.page_count,
        created_at=document.created_at,
    )


def _folder_for_document(document: Document, stored_category: str = "", stored_subcategory: str = "") -> tuple[str, str]:
    if stored_category.strip():
        return normalize_folder(stored_category, stored_subcategory)
    return guess_folder(
        document.original_filename or "",
        document.document_type or "",
        document.purpose_subtype or "",
    )


def _attach_folder_fields(document: Document, fields: dict[str, FieldHit], document_type: str) -> None:
    stored_cat = (fields.get(FOLDER_CATEGORY_FIELD).raw if fields.get(FOLDER_CATEGORY_FIELD) else "") or ""
    stored_sub = (fields.get(FOLDER_SUBCATEGORY_FIELD).raw if fields.get(FOLDER_SUBCATEGORY_FIELD) else "") or ""
    category, subcategory = _folder_for_document(
        document,
        stored_cat,
        stored_sub,
    )
    if not stored_cat:
        category, subcategory = guess_folder(
            document.original_filename or "",
            document_type or document.document_type or "",
            document.purpose_subtype or "",
        )
        category, subcategory = normalize_folder(category, subcategory)
    fields[FOLDER_CATEGORY_FIELD] = FieldHit(category, category, 0.9, "", 1)
    fields[FOLDER_SUBCATEGORY_FIELD] = FieldHit(subcategory, subcategory, 0.9, "", 1)


async def list_documents(db: AsyncSession, user: CurrentUser) -> list[DocumentOut]:
    result = await db.execute(
        select(Document)
        .where(
            Document.workspace_id == user.workspace_id,
            Document.processing_status.notin_(_NOT_STORED_STATUSES),
        )
        .order_by(Document.created_at.desc())
    )
    documents = list(result.scalars().all())
    ids = [row.id for row in documents]
    dates: dict = {}
    folders: dict = {}
    if ids:
        fields = await db.execute(
            select(ExtractionField).where(
                ExtractionField.document_id.in_(ids),
                ExtractionField.workspace_id == user.workspace_id,
                ExtractionField.field_name.in_(_FOLDER_LOOKUP_FIELDS),
            )
        )
        priority = {name: index for index, name in enumerate(_IMPORTANT_DATE_FIELDS)}
        best: dict = {}
        folder_values: dict = {}
        for row in fields.scalars().all():
            value = row.raw_value or row.normalized_value
            if not value:
                continue
            if row.field_name in FOLDER_FIELD_NAMES:
                current = folder_values.setdefault(row.document_id, {})
                current[row.field_name] = value
                continue
            current = best.get(row.document_id)
            rank = priority.get(row.field_name, 99)
            if current is None or rank < current[0]:
                best[row.document_id] = (rank, value)
        dates = {doc_id: pair[1] for doc_id, pair in best.items()}
        folders = folder_values
    return [
        _to_out(
            row,
            dates.get(row.id),
            *_folder_for_document(
                row,
                (folders.get(row.id) or {}).get(FOLDER_CATEGORY_FIELD, ""),
                (folders.get(row.id) or {}).get(FOLDER_SUBCATEGORY_FIELD, ""),
            ),
        )
        for row in documents
    ]


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
            ExtractionField.field_name.in_(_FOLDER_LOOKUP_FIELDS),
        )
    )
    important_date = None
    stored_category = ""
    stored_subcategory = ""
    priority = {name: index for index, name in enumerate(_IMPORTANT_DATE_FIELDS)}
    best_rank = 99
    for field in date_row.scalars().all():
        value = field.raw_value or field.normalized_value
        if not value:
            continue
        if field.field_name == FOLDER_CATEGORY_FIELD:
            stored_category = value
            continue
        if field.field_name == FOLDER_SUBCATEGORY_FIELD:
            stored_subcategory = value
            continue
        rank = priority.get(field.field_name, 99)
        if rank < best_rank:
            best_rank = rank
            important_date = value
    folder_category, folder_subcategory = _folder_for_document(document, stored_category, stored_subcategory)
    return _to_out(document, important_date, folder_category, folder_subcategory)


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
            limit = settings.max_image_upload_bytes if extension in IMAGE_EXTENSIONS else settings.max_upload_bytes
            if total_size > limit:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Images must be 10 MB or smaller." if extension in IMAGE_EXTENSIONS else "File must be 20 MB or smaller.",
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to read this file.") from None

    if total_size == 0:
        await reject_quarantine()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

    try:
        await _assert_workspace_quota(db, user.workspace_id, total_size)
    except HTTPException:
        await reject_quarantine()
        raise

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
            Document.processing_status.notin_(_NOT_STORED_STATUSES),
        )
    )
    if existing.scalar_one_or_none() is not None:
        await reject_quarantine()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document has already been uploaded.",
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
            detail="Security scan is unavailable. Try again later.",
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

    page_count = 1
    if extension == ".pdf":
        try:
            async with storage.open_for_read(relative_key, location="quarantine") as quarantine_path:
                page_count, encrypted = inspect_pdf(quarantine_path)
        except Exception:
            await reject_quarantine()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to read this PDF.") from None
        if encrypted:
            await reject_quarantine()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password-protected PDFs are not supported.",
            )
        if page_count > settings.max_pdf_pages:
            await reject_quarantine()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This PDF exceeds the {settings.max_pdf_pages}-page limit.",
            )

    try:
        await storage.promote(relative_key)
    except Exception:
        await reject_quarantine()
        await storage.delete_permanent(relative_key)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to store this file.") from None

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
        page_count=page_count,
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


def _preview_hit(text: str, pages: list[tuple[int, str]], reason: str = "") -> FieldHit:
    lines = build_preview_lines(text)
    if reason:
        lines = [reason] + [line for line in lines if line != reason]
    if not lines:
        lines = [reason or "No text extracted yet."]
    preview = "\n".join(lines)
    return FieldHit(
        preview,
        "",
        0.8,
        lines[0][:200],
        pages[0][0] if pages else 1,
    )


def _preview_from_fields(
    fields: dict[str, FieldHit],
    important: list[str],
    labels: dict[str, str],
    pages: list[tuple[int, str]],
    reason: str = "",
) -> FieldHit:
    lines: list[str] = []
    if reason:
        lines.append(reason)
    for key in important:
        hit = fields.get(key)
        if not hit or not (hit.raw or hit.normalized):
            continue
        label = labels.get(key) or humanize_label(key)
        lines.append(f"{label}: {hit.raw or hit.normalized}")
    if len(lines) <= (1 if reason else 0):
        return _preview_hit("", pages, reason)
    preview = "\n".join(lines)
    return FieldHit(preview, "", 0.85, lines[0][:200], pages[0][0] if pages else 1)


def _with_field_meta(
    fields: dict[str, FieldHit],
    important: list[str],
    labels: dict[str, str],
) -> dict[str, FieldHit]:
    payload = dict(fields)
    keys_json = json.dumps(important)
    labels_json = json.dumps(labels)
    payload["_important_keys"] = FieldHit(keys_json, keys_json, 1.0, "", 1)
    payload["_field_labels"] = FieldHit(labels_json, labels_json, 1.0, "", 1)
    return payload


def _meta_from_values(values: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    important: list[str] = []
    labels: dict[str, str] = {}
    raw_keys = values.get("_important_keys") or ""
    raw_labels = values.get("_field_labels") or ""
    if raw_keys:
        try:
            parsed = json.loads(raw_keys)
            if isinstance(parsed, list):
                important = [str(item) for item in parsed if item]
        except json.JSONDecodeError:
            important = []
    if raw_labels:
        try:
            parsed_labels = json.loads(raw_labels)
            if isinstance(parsed_labels, dict):
                labels = {str(key): str(value) for key, value in parsed_labels.items()}
        except json.JSONDecodeError:
            labels = {}
    return important, labels


def _document_mime(document: Document, is_pdf: bool) -> str:
    mime = (document.detected_mime or "").strip()
    if mime:
        return mime
    extension = (document.extension or "").lower()
    if is_pdf or extension == ".pdf":
        return "application/pdf"
    if extension == ".png":
        return "image/png"
    return "image/jpeg"


def _empty_supported_fields(document_type: str) -> dict[str, FieldHit]:
    return {
        "documentType": FieldHit(document_type, document_type, 0.2, "", 1),
        "provider": empty_field(),
        "policyNumber": empty_field(),
        "startDate": empty_field(),
        "expiryDate": empty_field(),
        "premium": empty_field(),
    }


async def _clear_stored_file(document: Document) -> None:
    if not document.storage_key:
        return
    await get_storage().delete_permanent(document.storage_key)
    document.storage_key = None
    document.file_size = 0


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
    provider = get_provider()
    native_ai = bool(getattr(provider, "supports_native_files", False))

    pages: list[tuple[int, str]] = []
    file_bytes: bytes | None = None
    try:
        async with storage.open_for_read(document.storage_key, location="permanent") as path:
            file_bytes = await asyncio.to_thread(path.read_bytes)
            if is_pdf:
                pages = await asyncio.to_thread(extract_pdf_pages, path)
            elif native_ai:
                pages = [(1, "")]
            else:
                pages = await asyncio.to_thread(read_document_pages, path, False)
    except Exception:
        document.processing_status = "failed"
        await db.commit()
        return

    text = "\n".join(part for _, part in pages)
    document.page_count = document.page_count or len(pages) or 1
    normalized = NormalizedDocument(
        pages=pages or [(1, "")],
        is_pdf=is_pdf,
        is_image=not is_pdf,
        page_count=document.page_count,
        filename=document.original_filename or "",
    )
    mime_type = _document_mime(document, is_pdf)
    result: IntelligenceResult | None = None
    if native_ai:
        try:
            result = await asyncio.to_thread(
                lambda: provider.analyze(normalized, file_bytes=file_bytes, mime_type=mime_type)
            )
        except Exception:
            logger.exception("Gemini document intelligence failed; falling back to local extraction.")
            result = None
            if is_pdf and len(text.strip()) < 40:
                try:
                    async with storage.open_for_read(document.storage_key, location="permanent") as path:
                        pages = await asyncio.to_thread(ocr_pdf_pages, path)
                except Exception:
                    pages = pages or [(1, "")]
            elif not is_pdf:
                try:
                    async with storage.open_for_read(document.storage_key, location="permanent") as path:
                        ocr_text = await asyncio.to_thread(ocr_image, path)
                        pages = [(1, ocr_text)]
                except Exception:
                    pages = [(1, "")]
            text = "\n".join(part for _, part in pages)
            normalized = NormalizedDocument(
                pages=pages or [(1, "")],
                is_pdf=is_pdf,
                is_image=not is_pdf,
                page_count=document.page_count or len(pages) or 1,
                filename=document.original_filename or "",
            )

    if result is None:
        from dataclasses import replace

        from ..intelligence.local import LocalIntelligenceProvider

        local = LocalIntelligenceProvider()
        decision = local.classify(normalized)
        if decision.status == "supported":
            fields = guess_fields(pages)
            doc_type = normalize_document_type(fields["documentType"].raw)
            fields["documentType"] = FieldHit(doc_type, doc_type, fields["documentType"].confidence, "", 1)
            important = important_keys_for(doc_type, fields)
            result = IntelligenceResult(
                decision=replace(decision, document_type=doc_type),
                fields=fields,
                important_keys=important,
                field_labels={key: humanize_label(key) for key in important},
            )
        else:
            fields = local.extract(normalized, "Other")
            important = important_keys_for("Other", fields)
            result = IntelligenceResult(
                decision=decision,
                fields=fields,
                important_keys=important,
                field_labels={key: humanize_label(key) for key in important},
            )

    decision = result.decision
    fields = dict(result.fields)
    important = list(result.important_keys)
    labels = dict(result.field_labels)
    document.purpose_status = decision.status
    document.purpose_category = decision.category
    document.purpose_subtype = decision.subtype
    document.purpose_reason = user_facing_reason(decision.status, decision.reason)
    document.purpose_confidence = decision.confidence
    document.document_type = decision.document_type

    if decision.status in ("rejected", "not_useful"):
        fields = _empty_supported_fields("Other")
        fields["preview"] = _preview_hit(text, pages, document.purpose_reason or "")
        await _replace_fields(db, document, _with_field_meta(fields, [], {}))
        document.processing_status = "rejected"
        await _clear_stored_file(document)
        await db.commit()
        return

    if decision.status == "supported":
        raw_type = fields["documentType"].raw if fields.get("documentType") else decision.document_type
        doc_type = normalize_document_type(raw_type)
        document.document_type = doc_type
        fields["documentType"] = FieldHit(doc_type, doc_type, decision.confidence, "", 1)
        if not important:
            important = important_keys_for(doc_type, fields)
            labels = {key: humanize_label(key) for key in important}
        try:
            validate_extraction(doc_type, build_structured_payload(doc_type, fields))
        except ValueError:
            document.processing_status = "failed"
            await _replace_fields(db, document, _with_field_meta(fields, important, labels))
            await db.commit()
            return
        fields["preview"] = (
            _preview_hit(text, pages, "")
            if text.strip()
            else _preview_from_fields(fields, important, labels, pages)
        )
        document.processing_status = "ready_for_review"
    else:
        if not important:
            important = important_keys_for("Other", fields)
            labels = {key: humanize_label(key) for key in important}
        fields["preview"] = (
            _preview_hit(text, pages, document.purpose_reason or "")
            if text.strip()
            else _preview_from_fields(fields, important, labels, pages, document.purpose_reason or "")
        )
        document.processing_status = "needs_decision"
    _attach_folder_fields(document, fields, document.document_type or "")
    await _replace_fields(db, document, _with_field_meta(fields, important, labels))
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
    if (document.document_type or "").strip() == "Other" or (raw_type or "").strip() == "Other":
        display_type = "Other"

    structured = None
    try:
        hits = await _rows_to_field_hits(field_rows)
        if "documentType" not in hits:
            hits["documentType"] = FieldHit(type_id, type_id, 0.5, "", 1)
        payload = build_structured_payload(type_id, hits)
        structured = validate_extraction(type_id, payload).model_dump(mode="json")
    except ValueError:
        structured = None

    important, labels = _meta_from_values(values)
    by_name = {row.field_name: row for row in field_rows}
    hits_for_rank = await _rows_to_field_hits(field_rows)
    if not important:
        important = important_keys_for(type_id, hits_for_rank)
        labels = {key: labels.get(key) or humanize_label(key) for key in important}
    else:
        important = important_keys_for(type_id, hits_for_rank, declared=important)
        labels = {canonicalize_key(key) or key: labels.get(key) or humanize_label(key) for key in labels}

    hidden = hidden_review_keys(type_id)
    seen_canon: set[str] = set()
    seen_label_value: set[tuple[str, str]] = set()
    evidence_fields: list[ExtractedFieldOut] = []
    for key in important:
        canon = canonicalize_key(key) or key
        if canon in META_FIELD_NAMES or canon in hidden or canon in seen_canon:
            continue
        row = by_name.get(key) or by_name.get(canon)
        if row is None:
            row = next(
                (candidate for name, candidate in by_name.items() if canonicalize_key(name) == canon),
                None,
            )
        if row is None:
            continue
        value = (row.raw_value or row.normalized_value or "").strip()
        if not value:
            continue
        label = labels.get(canon) or labels.get(key) or humanize_label(canon)
        fingerprint = (label.casefold(), "".join(value.split()).casefold())
        if fingerprint in seen_label_value:
            continue
        seen_canon.add(canon)
        seen_label_value.add(fingerprint)
        evidence_fields.append(
            ExtractedFieldOut(
                name=canon,
                value=value,
                evidence=row.evidence_snippet or "",
                page=row.page_number or 1,
                confidence=float(row.confidence or 0),
                label=label,
            )
        )

    folder_category, folder_subcategory = _folder_for_document(
        document,
        values.get(FOLDER_CATEGORY_FIELD, ""),
        values.get(FOLDER_SUBCATEGORY_FIELD, ""),
    )
    purpose_kwargs = {
        "purposeStatus": document.purpose_status or "",
        "purposeReason": user_facing_reason(document.purpose_status or "", document.purpose_reason or ""),
        "purposeCategory": document.purpose_category or "",
        "folderCategory": folder_category,
        "folderSubcategory": folder_subcategory,
        "fields": evidence_fields,
        "structuredExtraction": structured,
    }

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
            **purpose_kwargs,
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
        **purpose_kwargs,
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
            detail="Document is still processing. Try again shortly.",
        )
    if document.processing_status == "needs_decision":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Choose whether to keep this file first.",
        )
    if document.processing_status in ("failed", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=document.purpose_reason or "Unable to process this document.",
        )

    doc_type_input = payload.documentType.strip()
    type_id = normalize_document_type(doc_type_input)
    if doc_type_input not in DOCUMENT_TYPES and type_id == "generic" and doc_type_input not in {
        "Important document",
        "generic",
        "Other",
    }:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a valid document type.")

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
        from ..intelligence.validate import looks_like_amount_key, looks_like_date_key

        if looks_like_date_key(name) or name in {
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
        if looks_like_amount_key(name) or name in {
            "premium",
            "amount_due",
            "total",
            "subtotal",
            "tax",
            "discount",
            "previous_balance",
            "current_charges",
        }:
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

    for key, raw in structured_edits.items():
        if key in META_FIELD_NAMES or key == "documentType":
            continue
        fields[key] = kept(key, raw, norm_for(key, raw))

    existing_meta = {name: (row.raw_value or row.normalized_value or "") for name, row in by_name.items()}
    important_keys, field_labels = _meta_from_values(existing_meta)
    for key in structured_edits:
        if key in META_FIELD_NAMES or key == "documentType":
            continue
        if key not in important_keys:
            important_keys.append(key)
        field_labels.setdefault(key, humanize_label(key))

    preview_row = by_name.get("preview")
    if preview_row:
        fields["preview"] = FieldHit(
            preview_row.raw_value or "",
            preview_row.normalized_value or "",
            float(preview_row.confidence or 0.8),
            preview_row.evidence_snippet or "",
            preview_row.page_number or 1,
        )
    fields = _with_field_meta(fields, important_keys, field_labels)
    if payload.folderCategory.strip() or payload.folderSubcategory.strip() or FOLDER_CATEGORY_FIELD in by_name:
        category, subcategory = normalize_folder(
            payload.folderCategory or (by_name.get(FOLDER_CATEGORY_FIELD).raw_value if by_name.get(FOLDER_CATEGORY_FIELD) else ""),
            payload.folderSubcategory
            or (by_name.get(FOLDER_SUBCATEGORY_FIELD).raw_value if by_name.get(FOLDER_SUBCATEGORY_FIELD) else ""),
        )
        fields[FOLDER_CATEGORY_FIELD] = kept(FOLDER_CATEGORY_FIELD, category, category)
        fields[FOLDER_SUBCATEGORY_FIELD] = kept(FOLDER_SUBCATEGORY_FIELD, subcategory, subcategory)

    try:
        validate_extraction(type_id, build_structured_payload(type_id, fields))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await _replace_fields(db, document, fields)
    document.document_type = type_id
    document.processing_status = "reviewed"
    await db.commit()
    return await get_extraction(db, user, document_id)


async def decide_purpose(
    db: AsyncSession,
    user: CurrentUser,
    document_id: UUID,
    decision: str,
) -> ExtractionOut:
    choice = decision.strip().lower()
    if choice not in {"keep", "discard"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose keep or discard.")

    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.workspace_id == user.workspace_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if document.processing_status != "needs_decision":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document does not need a decision.",
        )
    if choice == "discard":
        await delete_document(db, user, document_id)
        return ExtractionOut(
            documentType="Other",
            provider="",
            policyNumber="",
            startDate="",
            expiryDate="",
            premium="",
            previewTitle="Discarded",
            previewLines=["This file was not stored."],
            processingStatus="discarded",
            purposeStatus="unknown",
            purposeReason="This file was not stored.",
            purposeCategory="other",
            fields=[],
            structuredExtraction=None,
        )

    document.document_type = "Other"
    document.purpose_status = "unknown"
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
