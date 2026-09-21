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


def normalize_amount(raw: str) -> str:
    cleaned = (raw or "").replace(",", "")
    match = re.search(r"\d+(?:\.\d{1,2})?", cleaned)
    return match.group(0) if match else ""
