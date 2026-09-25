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

# Currency markers. OCR often misreads ₹ as the *letter* I or l glued to digits.
# Never treat digit "1" as currency — that strips the leading digit from real
# amounts (18,500.00 → 8,500.00; 10,00,000 → 0,00,000).
CURRENCY_PREFIX = (
    r"(?:₹|\u20b9|rs\.?\s*|inr\s+|inr(?=\d)|\$|€|(?<![A-Za-z0-9])[Il](?=\d))"
)
# Indian grouping (10,00,000 / 1,50,00,000) requires at least one 2-digit group
# before the final 3-digit group so we never match a bare ",00,000" fragment.
_INDIAN_AMOUNT = r"[0-9]{1,3}(?:,[0-9]{2})+,[0-9]{3}(?:\.[0-9]{1,2})?"
_WESTERN_AMOUNT = r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?"
_DECIMAL_AMOUNT = r"[0-9]+\.[0-9]{2}"
_BARE_AMOUNT = r"[0-9]{4,}(?:\.[0-9]{1,2})?"
AMOUNT_NUMBER = (
    r"(" + _INDIAN_AMOUNT + r"|" + _WESTERN_AMOUNT + r"|" + _DECIMAL_AMOUNT + r"|" + _BARE_AMOUNT + r")"
)
AMOUNT_RE = re.compile(CURRENCY_PREFIX + r"?\s*" + AMOUNT_NUMBER, re.IGNORECASE)
# Detect OCR/rupee-like prefixes so we can rewrite them to "INR <amount>".
# Letters I/l only — digit 1 is a valid amount digit, not a currency stand-in.
_RUPEE_LIKE_PREFIX_RE = re.compile(
    r"^(?:₹|\u20b9|rs\.?\s*|inr\s*|[Il])(?=\d|\s)",
    re.IGNORECASE,
)
# Bare calendar years must never be treated as monetary amounts.
_YEAR_LIKE_AMOUNT_RE = re.compile(r"^(?:19|20)\d{2}$")


def is_plausible_money_match(match: re.Match[str]) -> bool:
    """
    Reject standalone years (2025/2026/…) that AMOUNT_RE can match as 4-digit numbers.

    Accept when the token has currency/OCR prefix, thousands separators, or decimals.
    """
    full = match.group(0) or ""
    number = match.group(1) or ""
    if _RUPEE_LIKE_PREFIX_RE.search(full) or re.search(r"[₹$€]", full):
        return True
    if re.match(r"^(?:rs\.?|inr|usd|eur)\b", full.strip(), flags=re.IGNORECASE):
        return True
    if "," in number or "." in number:
        return True
    if _YEAR_LIKE_AMOUNT_RE.fullmatch(number):
        return False
    return True


def find_amount_match(text: str) -> re.Match[str] | None:
    """First plausible monetary match in text (skips year-like bare integers)."""
    for found in AMOUNT_RE.finditer(text or ""):
        if is_plausible_money_match(found):
            return found
    return None


def focused_amount_evidence(context: str, amount_token: str, *, radius: int = 36, limit: int = 120) -> str:
    """Keep evidence close to the amount token instead of a huge OCR window."""
    ctx = " ".join((context or "").split())
    token = (amount_token or "").strip()
    if not ctx:
        return token[:limit]
    if not token:
        return ctx[:limit]
    lower = ctx.lower()
    idx = lower.find(token.lower())
    if idx < 0:
        # Fall back to the numeric core (without currency words).
        core = re.sub(r"^(?:₹|\u20b9|rs\.?\s*|inr\s*)", "", token, flags=re.IGNORECASE).strip()
        idx = lower.find(core.lower()) if core else -1
        token = core if idx >= 0 else token
    if idx < 0:
        return ctx[:limit]
    start = max(0, idx - radius)
    end = min(len(ctx), idx + len(token) + radius)
    snippet = ctx[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(ctx):
        snippet = snippet + "…"
    return snippet[:limit]


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
    """Normalize money strings to a plain number; tolerate OCR ₹→I/l and 'INR '."""
    cleaned = (raw or "").strip()
    # Strip currency words/symbols and letter OCR stand-ins only — never digit "1".
    cleaned = re.sub(
        r"^(?:₹|\u20b9|rs\.?\s*|inr\s*|\$|€|[Il])\s*",
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
