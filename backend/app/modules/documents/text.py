import re
from datetime import date
from typing import NamedTuple

DATE_TOKEN = re.compile(
    r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+\d{2,4}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

# Currency markers. OCR often misreads ₹ as I / l / 1 glued to digits.
# Prefer matching explicit "INR " (with a little space) as well as ₹ / Rs.
CURRENCY_PREFIX = (
    r"(?:₹|\u20b9|rs\.?\s*|inr\s+|inr(?=\d)|\$|€|(?<![A-Za-z0-9])[Il1](?=\d))"
)
AMOUNT_NUMBER = (
    r"([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?"
    r"|[0-9]+\.[0-9]{2}"
    r"|[0-9]{4,}(?:\.[0-9]{1,2})?)"
)
AMOUNT_RE = re.compile(CURRENCY_PREFIX + r"?\s*" + AMOUNT_NUMBER, re.IGNORECASE)
# Detect OCR/rupee-like prefixes so we can rewrite them to "INR <amount>".
_RUPEE_LIKE_PREFIX_RE = re.compile(
    r"^(?:₹|\u20b9|rs\.?\s*|inr\s*|[Il1])(?=\d|\s)",
    re.IGNORECASE,
)


class FieldHit(NamedTuple):
    raw: str
    normalized: str
    confidence: float
    evidence: str
    page: int


def empty_field(page: int = 1) -> FieldHit:
    return FieldHit("", "", 0.0, "", page)


def _year(value: str) -> int:
    year = int(value)
    if year < 100:
        return 2000 + year
    return year


def normalize_date(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3))).isoformat()
        except ValueError:
            return ""
    named = re.fullmatch(
        r"(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+(\d{2,4})",
        text,
        flags=re.IGNORECASE,
    )
    if named:
        month = MONTHS[named.group(2).lower().rstrip(".")]
        try:
            return date(_year(named.group(3)), month, int(named.group(1))).isoformat()
        except ValueError:
            return ""
    numeric = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", text)
    if numeric:
        try:
            return date(_year(numeric.group(3)), int(numeric.group(2)), int(numeric.group(1))).isoformat()
        except ValueError:
            return ""
    return ""


def canonicalize_amount_raw(raw: str) -> str:
    """
    Rewrite rupee / OCR currency prefixes to a stable display form: 'INR <amount>'.

    Examples:
      I42,000.00  → INR 42,000.00
      ₹7,560.00   → INR 7,560.00
      INR42000    → INR 42000
      INR 49560   → INR 49560
    """
    text = (raw or "").strip()
    if not text:
        return ""
    match = AMOUNT_RE.search(text)
    if not match:
        return text
    number_token = match.group(1)
    head = text[: match.start(1)]
    if _RUPEE_LIKE_PREFIX_RE.search(head) or _RUPEE_LIKE_PREFIX_RE.match(text):
        return f"INR {number_token}"
    # Already had an explicit non-INR currency (USD/EUR/$/€) — keep original match.
    if re.search(r"(?:\$|€|usd|eur)", head, flags=re.IGNORECASE):
        return match.group(0).strip()
    # Bare number matched with no prefix — leave as-is.
    if not head.strip():
        return number_token
    return f"INR {number_token}"


def normalize_amount(raw: str) -> str:
    """Normalize money strings to a plain number; tolerate OCR ₹→I/l/1 and 'INR '."""
    cleaned = (raw or "").strip()
    cleaned = re.sub(
        r"^(?:₹|\u20b9|rs\.?\s*|inr\s*|\$|€|[Il1])\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.replace(",", "")
    match = re.search(r"\d+(?:\.\d{1,2})?", cleaned)
    if not match:
        return ""
    value = match.group(0)
    if re.fullmatch(r"\d+\.0{1,2}", value):
        return value.split(".", 1)[0]
    return value
