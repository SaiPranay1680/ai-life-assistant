"""User-facing document folders auto-filled from extraction, then confirmed on review."""

from __future__ import annotations

FOLDER_TAXONOMY: dict[str, tuple[str, ...]] = {
    "Health": ("Insurance", "Appointment", "Prescription", "Records"),
    "Vehicle": ("Insurance", "Driving licence", "Registration", "Records"),
    "Home": ("Bills", "Warranty", "Records"),
    "Identity": ("Passport", "PAN", "Aadhaar", "Records"),
    "Purchases": ("Receipts", "Invoice", "Warranty"),
    "Insurance": ("Policies", "Health", "Vehicle"),
    "Records": ("Other",),
}

FOLDER_CATEGORY_FIELD = "folder_category"
FOLDER_SUBCATEGORY_FIELD = "folder_subcategory"
FOLDER_FIELD_NAMES = (FOLDER_CATEGORY_FIELD, FOLDER_SUBCATEGORY_FIELD)


def normalize_folder(category: str, subcategory: str) -> tuple[str, str]:
    cat = (category or "").strip()
    sub = (subcategory or "").strip()
    if cat not in FOLDER_TAXONOMY:
        guessed = guess_folder(cat or sub, cat, sub)
        cat, sub = guessed
    options = FOLDER_TAXONOMY[cat]
    if sub not in options:
        lowered = sub.lower()
        match = next((item for item in options if item.lower() == lowered), options[0])
        sub = match
    return cat, sub


def guess_folder(filename: str = "", document_type: str = "", subtype: str = "") -> tuple[str, str]:
    hay = " ".join(part for part in (filename, document_type, subtype) if part).lower().replace("_", " ")

    if "passport" in hay:
        return "Identity", "Passport"
    if " pan" in f" {hay}" or "permanent account" in hay or hay.startswith("pan"):
        return "Identity", "PAN"
    if "aadhaar" in hay or "aadhar" in hay:
        return "Identity", "Aadhaar"
    if "licen" in hay or "driving" in hay:
        return "Vehicle", "Driving licence"
    if any(token in hay for token in ("health", "medical", "hospital", "star health", "appointment", "clinic")):
        if "appoint" in hay:
            return "Health", "Appointment"
        if "prescription" in hay or "rx" in hay:
            return "Health", "Prescription"
        if "insur" in hay or "policy" in hay:
            return "Health", "Insurance"
        return "Health", "Records"
    if any(token in hay for token in ("car", "motor", "vehicle", "auto", "four wheeler")):
        if "insur" in hay or "policy" in hay:
            return "Vehicle", "Insurance"
        if "regist" in hay or "rc book" in hay:
            return "Vehicle", "Registration"
        return "Vehicle", "Records"
    if "warrant" in hay:
        return "Purchases", "Warranty"
    if any(token in hay for token in ("invoice", "receipt", "purchase")):
        return "Purchases", "Invoice" if "invoice" in hay else "Receipts"
    if any(token in hay for token in ("electric", "bescom", "utility", "water bill", "gas bill", "broadband", "bill")):
        return "Home", "Bills"
    if "insur" in hay or "policy" in hay:
        return "Insurance", "Policies"
    return "Records", "Other"
