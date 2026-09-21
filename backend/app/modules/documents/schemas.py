from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


DocumentTypeId = Literal[
    "utility_bill",
    "insurance",
    "purchase_receipt",
    "warranty",
    "generic",
]


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
    provider: str = ""
    policyNumber: str = ""
    startDate: str = ""
    expiryDate: str = ""
    premium: str = ""
    # Type-specific raw string edits from the review UI (e.g. bill_number, due_date).
    structuredFields: dict[str, str] | None = None


class EvidenceSnippet(BaseModel):
    page_number: int = Field(ge=1)
    snippet: str


class ExtractedValue(BaseModel):
    """Reusable extracted field with raw/normalized values, confidence, and evidence."""

    raw: str | None = None
    normalized: str | None = None
    confidence: float | None = None
    evidence: list[EvidenceSnippet] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value < 0.0 or value > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class ReceiptItemExtraction(BaseModel):
    name: ExtractedValue | None = None
    quantity: ExtractedValue | None = None
    unit_price: ExtractedValue | None = None
    amount: ExtractedValue | None = None
    total: ExtractedValue | None = None


class KeyValueExtraction(BaseModel):
    key: ExtractedValue | None = None
    value: ExtractedValue | None = None


class UtilityBillExtraction(BaseModel):
    document_type: ExtractedValue
    provider: ExtractedValue | None = None
    bill_number: ExtractedValue | None = None
    customer_id: ExtractedValue | None = None
    account_number: ExtractedValue | None = None
    billing_period_start: ExtractedValue | None = None
    billing_period_end: ExtractedValue | None = None
    due_date: ExtractedValue | None = None
    amount_due: ExtractedValue | None = None
    service_address: ExtractedValue | None = None
    previous_balance: ExtractedValue | None = None
    current_charges: ExtractedValue | None = None
    currency: ExtractedValue | None = None


class InsuranceExtraction(BaseModel):
    document_type: ExtractedValue
    provider: ExtractedValue | None = None
    policy_number: ExtractedValue | None = None
    policy_holder: ExtractedValue | None = None
    effective_date: ExtractedValue | None = None
    expiry_date: ExtractedValue | None = None
    premium: ExtractedValue | None = None
    deductible: ExtractedValue | None = None
    coverage: ExtractedValue | None = None
    currency: ExtractedValue | None = None


class PurchaseReceiptExtraction(BaseModel):
    document_type: ExtractedValue
    merchant: ExtractedValue | None = None
    receipt_number: ExtractedValue | None = None
    purchase_date: ExtractedValue | None = None
    transaction_date: ExtractedValue | None = None
    items: list[ReceiptItemExtraction] | None = None
    subtotal: ExtractedValue | None = None
    tax: ExtractedValue | None = None
    discount: ExtractedValue | None = None
    total: ExtractedValue | None = None
    payment_method: ExtractedValue | None = None
    currency: ExtractedValue | None = None


class WarrantyExtraction(BaseModel):
    document_type: ExtractedValue
    product: ExtractedValue | None = None
    brand: ExtractedValue | None = None
    model: ExtractedValue | None = None
    serial_number: ExtractedValue | None = None
    warranty_provider: ExtractedValue | None = None
    purchase_date: ExtractedValue | None = None
    warranty_start: ExtractedValue | None = None
    warranty_expiry: ExtractedValue | None = None
    warranty_duration: ExtractedValue | None = None


class GenericExtraction(BaseModel):
    document_type: ExtractedValue
    provider: ExtractedValue | None = None
    title: ExtractedValue | None = None
    document_date: ExtractedValue | None = None
    key_values: list[KeyValueExtraction] | None = None


StructuredExtraction = (
    UtilityBillExtraction
    | InsuranceExtraction
    | PurchaseReceiptExtraction
    | WarrantyExtraction
    | GenericExtraction
)


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
    structuredExtraction: dict[str, Any] | None = None
