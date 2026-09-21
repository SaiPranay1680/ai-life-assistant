from typing import TypedDict


class FieldSchema(TypedDict):
    labels: tuple[str, ...]
    kind: str
    forbidden: tuple[str, ...]


SCHEMA_FIELDS: dict[str, dict[str, FieldSchema]] = {
    "Insurance": {
        "provider": {
            "labels": ("insurance", "insurer", "underwriter", "general insurance"),
            "kind": "provider",
            "forbidden": (),
        },
        "policyNumber": {
            "labels": ("policy no", "policy number", "policy #", "policy id"),
            "kind": "id",
            "forbidden": (),
        },
        "premium": {
            "labels": ("total premium", "net premium", "gross premium", "premium payable", "premium"),
            "kind": "amount",
            "forbidden": ("sum insured", "idv", "insured declared value", "sum assured", "coverage amount"),
        },
        "startDate": {
            "labels": ("policy start", "start date", "commencement", "valid from", "period of insurance", "policy period"),
            "kind": "date",
            "forbidden": (),
        },
        "expiryDate": {
            "labels": ("policy expiry", "expiry date", "end date", "valid till", "valid until", "renewal due"),
            "kind": "date",
            "forbidden": (),
        },
    },
    "Bill": {
        "provider": {
            "labels": ("electricity", "bescom", "utility", "broadband", "telecom", "credit card"),
            "kind": "provider",
            "forbidden": (),
        },
        "policyNumber": {
            "labels": ("consumer number", "account no", "account number", "ca number", "customer id", "connection no"),
            "kind": "id",
            "forbidden": (),
        },
        "premium": {
            "labels": ("amount due", "amount payable", "bill amount", "total due", "total amount", "current charges"),
            "kind": "amount",
            "forbidden": ("sum insured", "opening balance"),
        },
        "startDate": {
            "labels": ("bill period", "from date", "billing from", "period from"),
            "kind": "date",
            "forbidden": (),
        },
        "expiryDate": {
            "labels": ("due date", "pay by", "last date", "payment due"),
            "kind": "date",
            "forbidden": (),
        },
    },
    "Purchase": {
        "provider": {
            "labels": ("sold by", "merchant", "seller", "vendor", "billed by"),
            "kind": "provider",
            "forbidden": (),
        },
        "policyNumber": {
            "labels": ("invoice no", "invoice number", "receipt no", "order no", "bill no"),
            "kind": "id",
            "forbidden": (),
        },
        "premium": {
            "labels": ("grand total", "amount paid", "total amount", "invoice total", "net payable"),
            "kind": "amount",
            "forbidden": ("sum insured",),
        },
        "startDate": {
            "labels": ("invoice date", "receipt date", "purchase date", "order date"),
            "kind": "date",
            "forbidden": (),
        },
        "expiryDate": {
            "labels": ("due date", "payment due", "pay by"),
            "kind": "date",
            "forbidden": (),
        },
    },
    "Warranty": {
        "provider": {
            "labels": ("warranty", "manufacturer", "brand"),
            "kind": "provider",
            "forbidden": (),
        },
        "policyNumber": {
            "labels": ("serial no", "serial number", "warranty no", "invoice no"),
            "kind": "id",
            "forbidden": (),
        },
        "premium": {
            "labels": ("purchase amount", "price", "amount paid"),
            "kind": "amount",
            "forbidden": ("sum insured",),
        },
        "startDate": {
            "labels": ("purchase date", "warranty start", "start date"),
            "kind": "date",
            "forbidden": (),
        },
        "expiryDate": {
            "labels": ("warranty expiry", "valid until", "valid till", "expires on"),
            "kind": "date",
            "forbidden": (),
        },
    },
    "Important document": {
        "provider": {
            "labels": ("government of", "ministry", "passport", "transport", "uidai"),
            "kind": "provider",
            "forbidden": (),
        },
        "policyNumber": {
            "labels": ("passport no", "passport number", "dl no", "licence no", "document no"),
            "kind": "id",
            "forbidden": (),
        },
        "startDate": {
            "labels": ("date of issue", "issued on", "valid from"),
            "kind": "date",
            "forbidden": (),
        },
        "expiryDate": {
            "labels": ("date of expiry", "valid until", "valid till", "expires"),
            "kind": "date",
            "forbidden": (),
        },
    },
    "Other": {
        "expiryDate": {
            "labels": ("deadline", "submission date", "due date", "last date"),
            "kind": "date",
            "forbidden": (),
        },
    },
}

DOCUMENT_TYPES = (
    "Bill",
    "Insurance",
    "Purchase",
    "Warranty",
    "Important document",
    "Other",
)
