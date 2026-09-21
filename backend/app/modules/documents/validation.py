from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import (
    GenericExtraction,
    InsuranceExtraction,
    PurchaseReceiptExtraction,
    StructuredExtraction,
    UtilityBillExtraction,
    WarrantyExtraction,
)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MIME_EXTENSION_MAP = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}

EXTRACTION_SCHEMA_REGISTRY: dict[str, type[StructuredExtraction]] = {
    "utility_bill": UtilityBillExtraction,
    "insurance": InsuranceExtraction,
    "purchase_receipt": PurchaseReceiptExtraction,
    "warranty": WarrantyExtraction,
    "generic": GenericExtraction,
}


def safe_filename(filename: str | None) -> str:
    return Path(filename or "upload").name


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, JPG or PNG files are allowed.")
    return extension


def detect_mime(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "application/octet-stream"


def validate_file_type(extension: str, detected_mime: str) -> None:
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise ValueError("File contents are not a PDF, JPG or PNG.")
    if extension not in MIME_EXTENSION_MAP[detected_mime]:
        raise ValueError("File type does not match the file extension.")


def validate_extraction(document_type: str, data: dict[str, Any]) -> StructuredExtraction:
    """
    Select the per-type Pydantic schema, validate extracted data, and return it.

    Unknown/null fields are allowed. Invalid document types and out-of-range
    confidence values are rejected. Insurance subtypes (car/health) share the
    insurance schema.
    """
    from .extract import DOCUMENT_TYPE_IDS, DOCUMENT_TYPE_LABELS, schema_document_type

    raw = (document_type or "").strip()
    if not raw:
        raise ValueError("Unsupported document type: ''")

    lowered = raw.lower().replace("-", "_").replace(" ", "_")
    if raw in EXTRACTION_SCHEMA_REGISTRY:
        type_id = raw
    elif lowered in EXTRACTION_SCHEMA_REGISTRY:
        type_id = lowered
    elif raw in DOCUMENT_TYPE_LABELS.values():
        type_id = next(key for key, label in DOCUMENT_TYPE_LABELS.items() if label == raw)
    elif lowered in DOCUMENT_TYPE_IDS:
        type_id = lowered
    else:
        raise ValueError(f"Unsupported document type: {document_type!r}")

    schema_key = schema_document_type(type_id)
    schema_cls = EXTRACTION_SCHEMA_REGISTRY.get(schema_key)
    if schema_cls is None:
        raise ValueError(f"Unsupported document type: {document_type!r}")
    try:
        return schema_cls.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
