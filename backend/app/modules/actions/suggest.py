from datetime import date

from ...models.documents import Document
from ...models.extraction import ExtractionField


def _value(fields: dict[str, ExtractionField], name: str) -> str:
    row = fields.get(name)
    if row is None:
        return ""
    return (row.raw_value or row.normalized_value or "").strip()


def _iso_date(fields: dict[str, ExtractionField], name: str) -> date | None:
    row = fields.get(name)
    if row is None:
        return None
    raw = (row.normalized_value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _label(raw: str, due: date | None) -> str:
    if raw:
        return raw
    if due:
        return f"{due.day} {due.strftime('%b %Y')}"
    return ""


def _priority(action_type: str, due: date | None) -> str:
    if due is None:
        return "high" if action_type == "PAY" else "low" if action_type == "KEEP_FOR_RECORDS" else "medium"
    days = (due - date.today()).days
    if days <= 14:
        return "high"
    if days <= 45:
        return "medium"
    return "low"


def _looks_like_filename(value: str) -> bool:
    lower = value.lower().strip()
    return lower.endswith((".pdf", ".jpg", ".jpeg", ".png", ".webp"))


def _record_label(doc_type: str, filename: str, provider: str = "") -> str:
    hay = f"{doc_type} {filename} {provider}".lower()
    for token, label in (
        ("passport", "passport"),
        ("aadhaar", "Aadhaar"),
        ("aadhar", "Aadhaar"),
        ("pan", "PAN"),
        ("licen", "driving licence"),
        ("invoice", "invoice"),
        ("purchase", "purchase"),
        ("receipt", "receipt"),
        ("warranty", "warranty"),
        ("insurance", "policy"),
        ("policy", "policy"),
        ("bill", "bill"),
    ):
        if token in hay:
            return label
    return "this document"


def _subject(provider: str, doc_type: str, filename: str) -> str:
    value = (provider or "").strip()
    if value and value.lower() != "this document" and not _looks_like_filename(value):
        return value
    kind = _record_label(doc_type, filename, value)
    return kind if kind == "this document" else f"this {kind}"


def _evidence(document: Document, fields: dict[str, ExtractionField], field_name: str) -> str:
    del document, fields, field_name
    return "From the details you confirmed."


def _item(
    action_type: str,
    title: str,
    due,
    due_label: str,
    explanation: str,
    evidence: str,
    reminder_default: str,
    confidence: float,
) -> dict:
    return {
        "action_type": action_type,
        "title": title,
        "due_at": due,
        "due_label": due_label,
        "priority": _priority(action_type, due),
        "confidence": confidence,
        "explanation": explanation,
        "evidence": evidence,
        "reminder_default": reminder_default,
    }


def suggestions_for(document: Document, fields: dict[str, ExtractionField]) -> list[dict]:
    doc_type = (document.document_type or _value(fields, "documentType")).lower()
    expiry_raw = (
        _value(fields, "expiryDate")
        or _value(fields, "due_date")
        or _value(fields, "expiry_date")
        or _value(fields, "warranty_expiry")
        or _value(fields, "warranty_end")
    )
    due = (
        _iso_date(fields, "expiryDate")
        or _iso_date(fields, "due_date")
        or _iso_date(fields, "expiry_date")
        or _iso_date(fields, "warranty_expiry")
        or _iso_date(fields, "warranty_end")
    )
    amount = (
        _value(fields, "premium")
        or _value(fields, "amount_due")
        or _value(fields, "total")
    )
    identifier = (
        _value(fields, "policyNumber")
        or _value(fields, "bill_number")
        or _value(fields, "policy_number")
        or _value(fields, "receipt_number")
        or _value(fields, "serial_number")
        or _value(fields, "service_number")
        or _value(fields, "account_number")
        or _value(fields, "customer_id")
    )
    filename = document.original_filename or "document"
    provider = (
        _value(fields, "provider")
        or _value(fields, "merchant")
        or _value(fields, "warranty_provider")
        or "this document"
    )
    subject = _subject(provider, doc_type, filename)
    evidence_due = (
        "due_date"
        if _value(fields, "due_date")
        else "warranty_expiry"
        if _value(fields, "warranty_expiry")
        else "expiry_date"
        if _value(fields, "expiry_date")
        else "expiryDate"
    )
    evidence_amount = "amount_due" if _value(fields, "amount_due") else "premium"

    if "insurance" in doc_type and expiry_raw:
        return [
            _item(
                "RENEW",
                f"Renew {subject}",
                due,
                _label(expiry_raw, due),
                f"Premium {amount} is due. Policy expires on {expiry_raw}."
                if amount
                else f"Your current policy expires on {expiry_raw}.",
                _evidence(document, fields, "expiryDate"),
                "Remind me 30 days before",
                0.8,
            )
        ]

    if "bill" in doc_type and (expiry_raw or amount):
        if amount and expiry_raw:
            reason = f"Amount {amount} is due on {expiry_raw}."
        elif amount:
            reason = f"Amount {amount} is due."
        else:
            reason = f"A bill is due on {expiry_raw}."
        return [
            _item(
                "PAY",
                f"Pay {subject}",
                due,
                _label(expiry_raw, due) or "Due date not confirmed",
                reason,
                _evidence(document, fields, evidence_due if expiry_raw else evidence_amount),
                "Remind me 3 days before",
                0.75 if expiry_raw else 0.6,
            )
        ]

    if ("purchase" in doc_type or "invoice" in doc_type) and (expiry_raw or amount):
        reason = f"Amount {amount} is due on {expiry_raw}." if amount and expiry_raw else (
            f"Amount {amount} is due." if amount else f"This invoice is due on {expiry_raw}."
        )
        return [
            _item(
                "PAY",
                f"Pay {subject}",
                due,
                _label(expiry_raw, due) or "Due date not confirmed",
                reason,
                _evidence(document, fields, "expiryDate" if expiry_raw else "premium"),
                "Remind me 7 days before",
                0.7,
            )
        ]

    if "warranty" in doc_type:
        reason = (
            f"Review warranty coverage before {expiry_raw}."
            if expiry_raw
            else "Review warranty coverage and keep this on file."
        )
        return [
            _item(
                "REVIEW",
                f"Review {subject} warranty",
                due,
                _label(expiry_raw, due) or "No expiry confirmed",
                reason,
                _evidence(document, fields, evidence_due if expiry_raw else "documentType"),
                "Remind me 14 days before",
                0.7 if expiry_raw else 0.5,
            )
        ]

    if "purchase" in doc_type or "invoice" in doc_type:
        if identifier:
            return [
                _item(
                    "REGISTER",
                    f"Register {subject} purchase",
                    due,
                    _label(expiry_raw, due),
                    f"Keep invoice {identifier} and register the purchase if required.",
                    _evidence(document, fields, "policyNumber"),
                    "Remind me 14 days before",
                    0.55,
                )
            ]
        return [
            _item(
                "KEEP_FOR_RECORDS",
                f"Keep {_record_label(doc_type, filename, provider)} on file",
                None,
                "",
                "Store this purchase receipt for your records. No payment date was confirmed.",
                _evidence(document, fields, "documentType"),
                "Remind me 30 days before",
                0.5,
            )
        ]

    if expiry_raw:
        return [
            _item(
                "FOLLOW_UP",
                f"Follow up on {subject}",
                due,
                _label(expiry_raw, due),
                f"A date of {expiry_raw} was confirmed on this document.",
                _evidence(document, fields, "expiryDate"),
                "Remind me 14 days before",
                0.55,
            )
        ]

    return [
        _item(
            "KEEP_FOR_RECORDS",
            f"Keep {_record_label(doc_type, filename, provider)} on file",
            None,
            "",
            "Keep this important document on file. No due date was confirmed.",
            _evidence(document, fields, "documentType"),
            "Remind me 30 days before",
            0.5,
        )
    ]
