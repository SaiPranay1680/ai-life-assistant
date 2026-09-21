from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    original_filename: str
    document_type: str | None
    processing_status: str
    important_date: str | None = None
    purpose_status: str | None = None
    purpose_reason: str | None = None
    purpose_category: str | None = None
    page_count: int | None = None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    id: UUID
    status: str
    original_filename: str


class ExtractionUpdate(BaseModel):
    documentType: str
    provider: str
    policyNumber: str
    startDate: str
    expiryDate: str
    premium: str


class PurposeDecisionIn(BaseModel):
    decision: str


class ExtractedFieldOut(BaseModel):
    name: str
    value: str
    evidence: str
    page: int
    confidence: float


class ExtractionOut(BaseModel):
    documentType: str
    provider: str
    policyNumber: str
    startDate: str
    expiryDate: str
    premium: str
    previewTitle: str
    previewLines: list[str]
    processingStatus: str
    purposeStatus: str = ""
    purposeReason: str = ""
    purposeCategory: str = ""
    fields: list[ExtractedFieldOut] = []
