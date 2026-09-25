"""Field / date / amount / evidence / confidence / action comparison helpers."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.documents.text import normalize_amount, normalize_date

from .config import AMOUNT_FIELDS, DATE_FIELDS, SKIP_UNEXPECTED


def dates_equivalent(expected: str | None, actual: str | None) -> bool:
    """True when both sides normalize to the same ISO date."""
    if expected is None or actual is None:
        return False
    left = normalize_date(str(expected).strip()) or str(expected).strip()
    right = normalize_date(str(actual).strip()) or str(actual).strip()
    if not left or not right:
        return False
    # If one side already ISO and the other needs normalize_date:
    left_iso = normalize_date(left) or left
    right_iso = normalize_date(right) or right
    return left_iso == right_iso


def amount_to_decimal(value: str | None) -> Decimal | None:
    """Normalize currency / OCR artifacts to a Decimal (2 dp)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    cleaned = normalize_amount(text)
    if not cleaned:
        # Fallback: strip symbols and commas ourselves.
        cleaned = (
            text.replace(",", "")
            .replace("₹", "")
            .replace("\u20b9", "")
            .replace("INR", "")
            .replace("Rs", "")
            .replace("rs", "")
            .replace("$", "")
            .strip()
        )
        # OCR rupee-as-letter-I/l prefix (never strip a leading digit "1").
        if cleaned[:1] in {"I", "l"} and len(cleaned) > 1 and cleaned[1].isdigit():
            cleaned = cleaned[1:]
        match_digits = "".join(ch for ch in cleaned if ch.isdigit() or ch == ".")
        cleaned = match_digits
    if not cleaned:
        return None
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def amounts_equivalent(expected: str | None, actual: str | None) -> bool:
    left = amount_to_decimal(expected)
    right = amount_to_decimal(actual)
    if left is None or right is None:
        return False
    return left == right


def _pick_compare_value(spec: dict[str, Any] | str | None) -> str | None:
    if spec is None:
        return None
    if isinstance(spec, str):
        return spec
    if not isinstance(spec, dict):
        return str(spec)
    for key in ("normalized", "raw"):
        value = spec.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _actual_value_dict(structured: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    raw = structured.get(field_name)
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return None


def _actual_display(value: dict[str, Any] | None) -> str | None:
    if not value:
        return None
    for key in ("normalized", "raw"):
        part = value.get(key)
        if part is not None and str(part).strip():
            return str(part).strip()
    return None


def _evidence_blob(value: dict[str, Any] | None) -> tuple[str, list[int]]:
    if not value:
        return "", []
    evidence = value.get("evidence") or []
    snippets: list[str] = []
    pages: list[int] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        snippet = str(item.get("snippet") or "")
        if snippet:
            snippets.append(snippet)
        page = item.get("page_number")
        if isinstance(page, int):
            pages.append(page)
    return "\n".join(snippets), pages


def evidence_matches(
    expected_spec: dict[str, Any],
    actual_value: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Soft evidence check: presence + optional page + substring containment.
    Does not require exact OCR string equality.
    """
    blob, pages = _evidence_blob(actual_value)
    require_evidence = bool(expected_spec.get("require_evidence", True))
    expected_page = expected_spec.get("page")
    contains = expected_spec.get("evidence_contains")
    if contains is None:
        contains = _pick_compare_value(expected_spec)

    presence_ok = (not require_evidence) or bool(blob.strip())
    page_ok = True
    if expected_page is not None:
        page_ok = int(expected_page) in pages if pages else False

    contains_ok = True
    if contains and blob:
        needle = str(contains).strip().lower()
        hay = blob.lower()
        # Also try amount/date-normalized needles without currency symbols.
        contains_ok = needle in hay or needle.replace(",", "") in hay.replace(",", "")
        if not contains_ok:
            # Last resort: digit run from expected appears in evidence.
            digits = "".join(ch for ch in needle if ch.isdigit())
            contains_ok = bool(digits) and digits in "".join(ch for ch in hay if ch.isdigit())
    elif contains and not blob:
        contains_ok = False

    return {
        "presence_ok": presence_ok,
        "page_ok": page_ok,
        "contains_ok": contains_ok,
        "actual_pages": pages,
        "evidence_snippet": blob[:200],
    }


def confidence_report(structured: dict[str, Any]) -> dict[str, Any]:
    with_conf = 0
    without_conf = 0
    invalid: list[dict[str, Any]] = []
    for name, value in structured.items():
        if name == "document_type" or not isinstance(value, dict):
            continue
        conf = value.get("confidence")
        if conf is None:
            # Empty/null fields don't count.
            if value.get("raw") or value.get("normalized"):
                without_conf += 1
            continue
        with_conf += 1
        try:
            number = float(conf)
        except (TypeError, ValueError):
            invalid.append({"field": name, "confidence": conf})
            continue
        if number < 0.0 or number > 1.0:
            invalid.append({"field": name, "confidence": number})
    return {
        "fields_with_confidence": with_conf,
        "fields_without_confidence": without_conf,
        "invalid_confidence_values": invalid,
    }


def compare_field(
    field_name: str,
    expected_spec: dict[str, Any] | str,
    actual_value: dict[str, Any] | None,
) -> dict[str, Any]:
    expected_text = _pick_compare_value(expected_spec if isinstance(expected_spec, dict) else {"normalized": expected_spec})
    actual_text = _actual_display(actual_value)
    spec = expected_spec if isinstance(expected_spec, dict) else {"normalized": expected_spec}

    if actual_text is None or actual_text == "":
        status = "missing"
        passed = False
    elif field_name in DATE_FIELDS:
        passed = dates_equivalent(expected_text, actual_text)
        status = "correct" if passed else "incorrect"
    elif field_name in AMOUNT_FIELDS:
        passed = amounts_equivalent(expected_text, actual_text)
        status = "correct" if passed else "incorrect"
    else:
        left = (expected_text or "").strip().lower()
        right = (actual_text or "").strip().lower()
        passed = left == right
        status = "correct" if passed else "incorrect"

    evidence = evidence_matches(spec, actual_value) if isinstance(spec, dict) else {
        "presence_ok": True,
        "page_ok": True,
        "contains_ok": True,
        "actual_pages": [],
        "evidence_snippet": "",
    }

    return {
        "field": field_name,
        "status": status,
        "passed": passed,
        "expected": expected_text,
        "actual": actual_text,
        "evidence": evidence,
        "is_date": field_name in DATE_FIELDS,
        "is_amount": field_name in AMOUNT_FIELDS,
    }


def compare_fields(
    expected_fields: dict[str, Any],
    structured: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for name, spec in expected_fields.items():
        results.append(compare_field(name, spec, _actual_value_dict(structured, name)))

    expected_names = set(expected_fields)
    for name, value in structured.items():
        if name in expected_names or name in SKIP_UNEXPECTED:
            continue
        if not isinstance(value, dict):
            continue
        if not (value.get("raw") or value.get("normalized")):
            continue
        results.append(
            {
                "field": name,
                "status": "unexpected",
                "passed": True,  # does not reduce field_accuracy denominator
                "expected": None,
                "actual": _actual_display(value),
                "evidence": {
                    "presence_ok": True,
                    "page_ok": True,
                    "contains_ok": True,
                    "actual_pages": [],
                    "evidence_snippet": "",
                },
                "is_date": name in DATE_FIELDS,
                "is_amount": name in AMOUNT_FIELDS,
            }
        )
    return results


def compare_actions(
    expected_actions: list[dict[str, Any]] | None,
    actual_actions: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """
    Compare product action suggestions by action_type.
    Extracting a date/amount alone is not an action — only real suggestions count.
    """
    expected = list(expected_actions or [])
    actual = list(actual_actions or [])

    expected_types = [str(item.get("action_type") or "").upper() for item in expected]
    actual_types = [str(item.get("action_type") or "").upper() for item in actual]

    expected_counts: dict[str, int] = {}
    for item in expected_types:
        expected_counts[item] = expected_counts.get(item, 0) + 1
    actual_counts: dict[str, int] = {}
    for item in actual_types:
        actual_counts[item] = actual_counts.get(item, 0) + 1

    false_actions: list[str] = []
    missing_actions: list[str] = []
    duplicate_actions: list[str] = []

    all_types = set(expected_counts) | set(actual_counts)
    for action_type in sorted(all_types):
        if not action_type:
            continue
        exp = expected_counts.get(action_type, 0)
        act = actual_counts.get(action_type, 0)
        if act > exp:
            # extras beyond expected
            for _ in range(act - exp):
                if exp == 0:
                    false_actions.append(action_type)
                else:
                    duplicate_actions.append(action_type)
        if exp > act:
            for _ in range(exp - act):
                missing_actions.append(action_type)

    # Also flag duplicate when actual has >1 of same type and expected had at most 1.
    for action_type, count in actual_counts.items():
        if count > 1 and action_type not in duplicate_actions and expected_counts.get(action_type, 0) <= 1:
            # already counted above when act > exp; ensure listed once if exp==1 and act==2
            pass

    return {
        "false_actions": false_actions,
        "missing_actions": missing_actions,
        "duplicate_actions": duplicate_actions,
        "expected_types": expected_types,
        "actual_types": actual_types,
    }
