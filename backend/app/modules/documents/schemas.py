from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    original_filename: str
    document_type: str | None
    processing_status: str
    important_date: str | None = None
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
