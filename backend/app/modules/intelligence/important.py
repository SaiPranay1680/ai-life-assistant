import re

from ..documents.extract import schema_document_type
from ..documents.text import FieldHit

META_FIELD_NAMES = frozenset(
    {"preview", "documentType", "_important_keys", "_field_labels", "folder_category", "folder_subcategory"}
)

# Canonical names so later actions (pay / renew) can find dates and amounts.
FIELD_ALIASES = {
    "amount_payable": "amount_due",
    "total_due": "amount_due",
    "bill_amount": "amount_due",
    "pay_amount": "amount_due",
    "premium_amount": "premium",
    "pay_before": "due_date",
    "payment_due_date": "due_date",
    "last_date_to_pay": "due_date",
    "policy_expiry_date": "expiry_date",
    "policy_expiration": "expiry_date",
    "policy_end_date": "expiry_date",
    "startdate": "effective_date",
    "start_date": "effective_date",
    "policy_start_date": "effective_date",
    "service_no": "service_number",
    "consumer_number": "service_number",
    "ca_number": "service_number",
    "connection_number": "service_number",
    "account_no": "account_number",
    "policy_no": "policy_number",
    "policynumber": "policy_number",
    "serial_no": "serial_number",
    "warranty_expiration": "warranty_expiry",
    "warranty_expiry_date": "warranty_expiry",
    "invoice_no": "invoice_number",
    "receipt_no": "receipt_number",
}

# Display ranking used only when the model did not declare important keys (local fallback).
TYPE_IMPORTANT_RANK = {
    "utility_bill": (
        "service_number",
        "account_number",
        "customer_id",
        "bill_number",
        "amount_due",
        "due_date",
        "provider",
    ),
    "insurance": (
        "policy_number",
        "premium",
        "coverage",
        "effective_date",
        "expiry_date",
        "policy_holder",
    ),
    "purchase_receipt": (
        "merchant",
        "receipt_number",
        "total",
        "purchase_date",
        "payment_method",
    ),
    "warranty": (
        "product",
        "serial_number",
        "purchase_date",
        "warranty_expiry",
        "warranty_provider",
        "brand",
    ),
    "generic": ("title", "document_date", "expiry_date"),
}

# Title-like fields that should not appear on the review form for these schemas.
HIDDEN_REVIEW_KEYS = {
    "insurance": frozenset({"provider", "title"}),
    "car_insurance": frozenset({"provider", "title"}),
    "health_insurance": frozenset({"provider", "title"}),
}

DISPLAY_LABELS = {
    "service_number": "Service Number",
    "account_number": "Account Number",
    "customer_id": "Customer ID",
    "bill_number": "Bill Number",
    "amount_due": "Amount to Pay",
    "due_date": "Pay Before",
    "provider": "Provider",
    "policy_number": "Policy Number",
    "policy_holder": "Policy Holder",
    "premium": "Premium",
    "coverage": "Coverage",
    "effective_date": "Policy Start",
    "expiry_date": "Expiry Date",
    "merchant": "Vendor",
    "receipt_number": "Invoice Number",
    "total": "Amount",
    "purchase_date": "Purchase Date",
    "product": "Product",
    "serial_number": "Serial Number",
    "warranty_expiry": "Warranty Expires",
    "warranty_provider": "Warranty Provider",
    "brand": "Brand",
    "title": "Title",
    "document_date": "Date",
}


def hidden_review_keys(document_type: str) -> frozenset[str]:
    schema = schema_document_type(document_type)
    return HIDDEN_REVIEW_KEYS.get(document_type, HIDDEN_REVIEW_KEYS.get(schema, frozenset()))


def canonicalize_key(key: str) -> str:
    text = (key or "").strip()
    if not text:
        return ""
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    lowered = snake.lower().replace("-", "_").replace(" ", "_")
    lowered = re.sub(r"_+", "_", lowered).strip("_")
    return FIELD_ALIASES.get(lowered, lowered)


def find_field(fields: dict[str, FieldHit], key: str) -> tuple[str, FieldHit | None]:
    canon = canonicalize_key(key) or key
    if canon in fields:
        return canon, fields[canon]
    if key in fields:
        return canon, fields[key]
    for name, hit in fields.items():
        if canonicalize_key(name) == canon:
            return canon, hit
    return canon, None


def humanize_label(key: str, provided: str = "") -> str:
    if provided.strip():
        return provided.strip()
    canon = canonicalize_key(key) or key
    if canon in DISPLAY_LABELS:
        return DISPLAY_LABELS[canon]
    if key in DISPLAY_LABELS:
        return DISPLAY_LABELS[key]
    return canon.replace("_", " ").replace("-", " ").strip().title() or key


def is_filled(hit: FieldHit | None) -> bool:
    return bool(hit and (hit.raw or hit.normalized))


def important_keys_for(
    document_type: str,
    fields: dict[str, FieldHit],
    declared: list[str] | None = None,
    limit: int = 8,
) -> list[str]:
    """Choose a short list of user-facing fields. Gemini supplies `declared`; local uses ranking."""
    seen: set[str] = set()
    selected: list[str] = []
    hidden = hidden_review_keys(document_type)

    def add(key: str) -> None:
        canon, hit = find_field(fields, key)
        if canon in META_FIELD_NAMES or canon in seen or canon in hidden:
            return
        if not is_filled(hit):
            return
        seen.add(canon)
        selected.append(canon)

    if declared:
        for key in declared:
            add(key)
            if len(selected) >= limit:
                return selected
        return selected

    ranked = TYPE_IMPORTANT_RANK.get(schema_document_type(document_type), TYPE_IMPORTANT_RANK["generic"])
    for key in ranked:
        add(key)
        if len(selected) >= limit:
            return selected
    if selected:
        return selected
    for key, hit in fields.items():
        if len(selected) >= limit:
            break
        if is_filled(hit):
            add(key)
    return selected
