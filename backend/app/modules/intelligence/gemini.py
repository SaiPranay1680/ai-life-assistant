from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from ...core.config import settings
from ..documents.extract import normalize_document_type
from ..documents.text import FieldHit
from .base import IntelligenceError
from .important import canonicalize_key, humanize_label, important_keys_for
from .types import (
    INVALID_DOCUMENT_REASON,
    IntelligenceResult,
    NormalizedDocument,
    PurposeDecision,
    user_facing_reason,
)
from .validate import validate_extracted_fields

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_MAX_TEXT_CHARS = 24_000
_MAX_FILE_BYTES = 20 * 1024 * 1024

UNDERSTAND_PROMPT = """You are the document intelligence engine for a personal AI life assistant.

First understand the uploaded document. It may be a native PDF or a photo/scan/screenshot of a document. A photo of a bill, policy, invoice, warranty, or ID is a valid document — set status to "supported".

Determine its document type. Do not rely on a fixed closed list — choose a precise type such as electricity_bill, mobile_postpaid_bill, health_insurance_policy, product_warranty, tax_invoice, or unknown.

Then identify ONLY information that would be important for the user to know, track, search, or take action on.

Examples (these are EXAMPLES, not a complete list):
- Electricity / utility / mobile bill: service/account/mobile number, amount payable, payment due date
- Insurance: policy number, premium, coverage, start date, expiry/renewal date
- Invoice: invoice number, vendor, amount, invoice date, payment due date
- Warranty: product, serial/model number, purchase date, warranty expiration

Ignore watermarks such as "synthetic", "test document", or "not valid" when the file still contains real bill, policy, invoice, or identity fields. Still extract those fields and set status to "supported".

For an unknown document type, still pick the few fields that matter to a person managing their life admin.
Never invent a field the document does not support.
Do not extract the document title as a provider/insurer field.
Never return the same fact twice under different keys (for example policy_number and policyNumber).
Do not include names, full addresses, tariff tables, meter readings, tax breakdowns, or other noise unless that is the only identifier the user would need.

Set status to "rejected" only when the file is not a life-admin document at all: a natural photo of people/scenery, a newspaper, empty/gibberish, or placeholder lorem ipsum. Do not reject a document because it is an image or a screenshot.
Keep reason to one short professional sentence.

Return JSON only.
"""

EXTRACT_PROMPT = """You are extracting a small set of actionable fields from a personal document.

Rules:
- Extract ONLY the requested fields.
- Never invent a value. If a value cannot be confidently determined, return an empty string.
- For every non-empty value, copy evidence text from the document that contains that value.
- For money, distinguish carefully between total, amount paid, amount due, previous balance, tax, and subtotal.
  The user almost always needs the current amount payable / amount due, not a running total or previous balance.
- Normalize dates to YYYY-MM-DD when possible.
- Normalize amounts to a plain number without currency symbols (example: 2600).
- Put the currency code in the currency field when the value is money (INR, USD, ...).
- confidence is 0 to 1.

Return JSON only.
"""


class ImportantFieldSpec(BaseModel):
    key: str
    label: str = ""
    kind: Literal["text", "id", "date", "amount", "currency"] = "text"
    reason: str = ""


class UnderstandModel(BaseModel):
    document_type: str = "unknown"
    document_purpose: str = ""
    status: Literal["supported", "unknown", "not_useful", "rejected"] = "unknown"
    reason: str = ""
    confidence: float = 0.5
    important_fields: list[ImportantFieldSpec] = Field(default_factory=list)


class ExtractedFieldModel(BaseModel):
    key: str
    label: str = ""
    value: str = ""
    normalized_value: str = ""
    currency: str = ""
    confidence: float = 0.0
    evidence_text: str = ""
    evidence_page: int = 1


class ExtractModel(BaseModel):
    fields: list[ExtractedFieldModel] = Field(default_factory=list)


def _parse_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise IntelligenceError("The model returned an empty response.")
    fenced = _JSON_FENCE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntelligenceError("The model did not return valid JSON.") from exc
    if not isinstance(payload, dict):
        raise IntelligenceError("The model JSON must be an object.")
    return payload


class GeminiClient:
    """Thin wrapper around google-genai so tests can inject a fake."""

    def __init__(self) -> None:
        try:
            from google import genai
        except ImportError as exc:
            raise IntelligenceError("google-genai is not installed.") from exc
        if not settings.gemini_api_key:
            raise IntelligenceError("GEMINI_API_KEY is not configured.")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model or "gemini-2.5-flash"

    def generate_json(self, contents: list[Any], schema: type[BaseModel]) -> dict[str, Any]:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as exc:
            raise IntelligenceError(f"Gemini request failed: {exc.__class__.__name__}") from exc
        text = getattr(response, "text", None) or ""
        if not text and getattr(response, "candidates", None):
            # Some SDK versions put JSON on the first candidate parts.
            try:
                parts = response.candidates[0].content.parts
                text = "".join(getattr(part, "text", "") or "" for part in parts)
            except Exception:
                text = ""
        return _parse_json(text)


def _file_part(file_bytes: bytes, mime_type: str):
    from google.genai import types

    return types.Part.from_bytes(data=file_bytes, mime_type=mime_type)


def _contents(
    document: NormalizedDocument,
    prompt: str,
    file_bytes: bytes | None,
    mime_type: str | None,
) -> list[Any]:
    parts: list[Any] = []
    if file_bytes and mime_type and len(file_bytes) <= _MAX_FILE_BYTES:
        try:
            parts.append(_file_part(file_bytes, mime_type))
        except Exception:
            logger.warning("Could not attach native file to Gemini; sending extracted text only.")
    excerpt = document.text.strip()
    if excerpt:
        parts.append(f"Filename: {document.filename}\n\nExtracted text (may be incomplete):\n{excerpt[:_MAX_TEXT_CHARS]}")
    elif document.filename:
        kind = "image" if document.is_image else "file"
        parts.append(
            f"Filename: {document.filename}\nThe {kind} is attached. Read the attached file even if there is little extracted text. "
            "A photo or scan of a bill, policy, invoice, or ID is a valid document."
        )
    parts.append(prompt)
    if len(parts) == 1:
        raise IntelligenceError("No document content was available for analysis.")
    return parts


_ACTIONABLE_TYPES = {
    "utility_bill",
    "insurance",
    "health_insurance",
    "car_insurance",
    "purchase_receipt",
    "warranty",
}
_ACTIONABLE_TOKENS = (
    "bill",
    "invoice",
    "receipt",
    "policy",
    "insurance",
    "warranty",
    "passport",
    "aadhaar",
    "aadhar",
    "pan",
    "licence",
    "license",
)


def _looks_like_life_admin(model: UnderstandModel, mapped: str) -> bool:
    if mapped in _ACTIONABLE_TYPES:
        return True
    hay = f"{model.document_type} {model.document_purpose}".lower()
    if any(token in hay for token in _ACTIONABLE_TOKENS):
        return True
    return len(model.important_fields) >= 2


def _purpose_from_understand(model: UnderstandModel) -> PurposeDecision:
    raw_type = (model.document_type or "unknown").strip() or "unknown"
    mapped = normalize_document_type(raw_type)
    status = model.status
    if status not in {"supported", "unknown", "not_useful", "rejected"}:
        status = "unknown"
    if status == "supported" and mapped == "generic" and "unknown" in raw_type.lower():
        status = "unknown"
    if status in {"unknown", "not_useful", "rejected"} and _looks_like_life_admin(model, mapped):
        status = "supported"
    reason = user_facing_reason(status, (model.reason or model.document_purpose or "").strip())
    if not reason:
        reason = f"{raw_type.replace('_', ' ')} identified."
    return PurposeDecision(
        status=status,
        document_type=mapped if status == "supported" else ("Other" if mapped == "generic" else mapped),
        category=mapped,
        subtype=raw_type.lower().replace(" ", "_")[:100],
        reason=reason[:500],
        confidence=max(0.0, min(float(model.confidence or 0.5), 1.0)),
    )


def _hits_from_extract(model: ExtractModel) -> tuple[dict[str, FieldHit], dict[str, str], list[str]]:
    fields: dict[str, FieldHit] = {}
    labels: dict[str, str] = {}
    order: list[str] = []
    for item in model.fields:
        key = canonicalize_key(item.key)
        if not key:
            continue
        value = str(item.value or "").strip()
        normalized = str(item.normalized_value or "").strip()
        if not value and not normalized:
            continue
        page = item.evidence_page if item.evidence_page and item.evidence_page > 0 else 1
        hit = FieldHit(
            value,
            normalized or value,
            max(0.0, min(float(item.confidence or 0.0), 1.0)),
            (item.evidence_text or "")[:200],
            page,
        )
        currency = str(item.currency or "").strip().upper()
        if currency and "currency" not in fields:
            fields["currency"] = FieldHit(currency, currency, 0.9, currency, page)
        if key in fields:
            existing = fields[key]
            if hit.confidence >= existing.confidence:
                fields[key] = hit
                labels[key] = humanize_label(key, item.label)
            continue
        fields[key] = hit
        labels[key] = humanize_label(key, item.label)
        order.append(key)
    return fields, labels, order


class GeminiIntelligenceProvider:
    supports_native_files = True

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client

    def _client_or_create(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def classify(self, document: NormalizedDocument) -> PurposeDecision:
        return self.analyze(document).decision

    def extract(self, document: NormalizedDocument, document_type: str) -> dict[str, FieldHit]:
        result = self.analyze(document)
        if document_type:
            result.fields["documentType"] = FieldHit(document_type, document_type, 0.8, "", 1)
        return result.fields

    def analyze(
        self,
        document: NormalizedDocument,
        *,
        file_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> IntelligenceResult:
        if document.page_count > 30:
            decision = PurposeDecision(
                status="rejected",
                document_type="Other",
                category="publication",
                subtype="too_many_pages",
                reason=INVALID_DOCUMENT_REASON,
                confidence=0.95,
            )
            return IntelligenceResult(decision=decision, fields={"documentType": FieldHit("Other", "Other", 0.95, "", 1)})

        client = self._client_or_create()
        understand_payload = client.generate_json(
            _contents(document, UNDERSTAND_PROMPT, file_bytes, mime_type),
            UnderstandModel,
        )
        understand = UnderstandModel.model_validate(understand_payload)
        decision = _purpose_from_understand(understand)
        if decision.status in {"rejected", "not_useful"}:
            return IntelligenceResult(
                decision=decision,
                fields={"documentType": FieldHit(decision.document_type, decision.document_type, decision.confidence, "", 1)},
            )

        specs = understand.important_fields[:8]
        if not specs:
            specs = [
                ImportantFieldSpec(key="title", label="Title", kind="text"),
                ImportantFieldSpec(key="document_date", label="Date", kind="date"),
            ]
        field_lines = "\n".join(
            f"- {spec.key} ({spec.kind}): {spec.label or spec.key}. {spec.reason}".strip()
            for spec in specs
        )
        extract_prompt = (
            EXTRACT_PROMPT
            + f"\n\nDocument type: {understand.document_type}\n"
            + f"Purpose: {understand.document_purpose}\n\n"
            + "Extract these fields:\n"
            + field_lines
        )
        extract_payload = client.generate_json(
            _contents(document, extract_prompt, file_bytes, mime_type),
            ExtractModel,
        )
        extracted = ExtractModel.model_validate(extract_payload)
        allowed = {canonicalize_key(spec.key) for spec in specs if canonicalize_key(spec.key)}
        fields, labels, order = _hits_from_extract(extracted)
        fields = {key: hit for key, hit in fields.items() if key in allowed or key == "currency"}
        labels = {key: label for key, label in labels.items() if key in fields}
        order = [key for key in order if key in fields]
        fields = validate_extracted_fields(fields, document.text)
        doc_type = decision.document_type if decision.status == "supported" else "Other"
        fields["documentType"] = FieldHit(doc_type, doc_type, decision.confidence, "", 1)
        important = important_keys_for(doc_type, fields, declared=order)
        kept_labels = {key: labels.get(key) or humanize_label(key) for key in important}
        return IntelligenceResult(
            decision=decision,
            fields=fields,
            important_keys=important,
            field_labels=kept_labels,
        )
