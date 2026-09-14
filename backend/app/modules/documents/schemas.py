from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    original_filename: str
    document_type: str | None
    processing_status: str
    created_at: datetime | None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    id: UUID
    status: str
    original_filename: str
