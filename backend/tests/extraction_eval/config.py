"""EVAL-001 configurable thresholds and field categorizations.

Thresholds default to 0.0 so the suite reports the measured baseline
instead of failing on currently imperfect extraction quality.
Raise them deliberately when locking a regression floor.
"""

from __future__ import annotations

# Soft floors for optional CI gating (fractions 0.0–1.0).
THRESHOLDS: dict[str, float] = {
    "classification_accuracy": 0.0,
    "field_accuracy": 0.0,
    "date_accuracy": 0.0,
    "amount_accuracy": 0.0,
    "evidence_presence_accuracy": 0.0,
    "evidence_page_accuracy": 0.0,
}

# DOC-005 field names treated as dates when scoring date accuracy.
DATE_FIELDS: frozenset[str] = frozenset(
    {
        "due_date",
        "billing_period_start",
        "billing_period_end",
        "effective_date",
        "expiry_date",
        "purchase_date",
        "transaction_date",
        "warranty_start",
        "warranty_expiry",
        "document_date",
        "startDate",
        "expiryDate",
    }
)

# DOC-005 field names treated as monetary amounts.
AMOUNT_FIELDS: frozenset[str] = frozenset(
    {
        "amount_due",
        "premium",
        "subtotal",
        "tax",
        "total",
        "discount",
        "previous_balance",
        "current_charges",
        "deductible",
        "coverage",
    }
)

# Fields skipped when counting unexpected extras (always present / complex).
SKIP_UNEXPECTED: frozenset[str] = frozenset(
    {
        "document_type",
        "items",
        "key_values",
        "currency",
    }
)
