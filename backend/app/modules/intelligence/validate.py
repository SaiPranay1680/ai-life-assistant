import re

from ..documents.text import FieldHit, normalize_amount, normalize_date
from .important import META_FIELD_NAMES, canonicalize_key

_CONFIDENCE_FLOOR = 0.45
_AMOUNT_HINTS = (
    "amount",
    "premium",
    "total",
    "price",
    "charge",
    "balance",
    "tax",
    "due",
    "coverage",
)


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def looks_like_date_key(name: str) -> bool:
    lowered = (name or "").lower()
    if lowered.endswith("date") or lowered.endswith("_start") or lowered.endswith("_end") or lowered.endswith("_expiry"):
        return True
    return any(token in lowered for token in ("expir", "pay_before", "valid_until", "valid_till"))


def looks_like_amount_key(name: str) -> bool:
    lowered = (name or "").lower()
    if looks_like_date_key(lowered):
        return False
    return any(token in lowered for token in _AMOUNT_HINTS)


def evidence_supports_value(hit: FieldHit, source_text: str = "") -> bool:
    if not (hit.raw or hit.normalized):
        return False
    haystacks = [hit.evidence or "", source_text]
    compact_raw = _compact(hit.raw)
    compact_norm = _compact(hit.normalized)
    for haystack in haystacks:
        compact_hay = _compact(haystack)
        if not compact_hay:
            continue
        if compact_raw and compact_raw in compact_hay:
            return True
        if compact_norm and len(compact_norm) >= 3 and compact_norm in compact_hay:
            return True
    # Images/PDFs sent natively may have no local text; keep evidence-backed values.
    if hit.evidence.strip() and not source_text.strip():
        return True
    return False


def normalize_hit(name: str, hit: FieldHit) -> FieldHit:
    raw = (hit.raw or "").strip()
    if looks_like_date_key(name):
        iso = normalize_date(hit.normalized or raw) or normalize_date(raw)
        if not iso:
            return FieldHit("", "", 0.0, hit.evidence, hit.page)
        return FieldHit(raw or iso, iso, hit.confidence, hit.evidence, hit.page)
    if looks_like_amount_key(name):
        amount = normalize_amount(hit.normalized or raw) or normalize_amount(raw)
        if not amount:
            return FieldHit("", "", 0.0, hit.evidence, hit.page)
        return FieldHit(raw or amount, amount, hit.confidence, hit.evidence, hit.page)
    return FieldHit(raw, (hit.normalized or raw).strip(), hit.confidence, hit.evidence, hit.page)


def validate_extracted_fields(
    fields: dict[str, FieldHit],
    source_text: str = "",
) -> dict[str, FieldHit]:
    """Drop invented / unparseable values. Keep meta fields untouched."""
    cleaned: dict[str, FieldHit] = {}
    for name, hit in fields.items():
        if name in META_FIELD_NAMES:
            cleaned[name] = hit
            continue
        key = canonicalize_key(name) or name
        if not (hit.raw or hit.normalized):
            continue
        if hit.confidence < _CONFIDENCE_FLOOR:
            continue
        normalized = normalize_hit(key, hit)
        if not (normalized.raw or normalized.normalized):
            continue
        if source_text.strip() and not evidence_supports_value(normalized, source_text):
            continue
        if not source_text.strip() and not (normalized.evidence or "").strip():
            continue
        cleaned[key] = normalized
    return cleaned
