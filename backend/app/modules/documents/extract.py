import json
import re
import tempfile
from pathlib import Path

import pymupdf

from .text import (
    AMOUNT_NUMBER,
    AMOUNT_RE,
    CURRENCY_PREFIX,
    DATE_TOKEN,
    FieldHit,
    canonicalize_amount_raw,
    empty_field,
    normalize_amount,
    normalize_date,
)

POLICY_RE = re.compile(
    r"(?:policy|account|invoice|bill|receipt)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})",
    re.IGNORECASE,
)
BILL_NUMBER_RE = re.compile(
    r"(?:bill|invoice)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})",
    re.IGNORECASE,
)
CUSTOMER_ID_RE = re.compile(
    r"(?:customer\s*(?:id|number|#)|cust\.?\s*id)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{3,})",
    re.IGNORECASE,
)
SERVICE_ADDRESS_RE = re.compile(
    r"service\s*address\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
BILLING_PERIOD_RANGE_RE = re.compile(
    r"billing\s*period\s*[:\-]?\s*"
    r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+\d{2,4}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})"
    r"\s*(?:[-–—]|to)\s+"
    r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+\d{2,4}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
# Document titles / headings that must never be treated as provider/merchant names.
PROVIDER_TITLE_RE = re.compile(
    r"^(utility\s*bill|electric(?:ity)?\s*bill|gas\s*bill|water\s*bill|bill|"
    r"purchase\s*receipt|tax\s*invoice|invoice|receipt|warranty(?:\s*card)?|"
    r"insurance(?:\s*policy)?|health\s*insurance(?:\s*policy)?|car\s*insurance(?:\s*policy)?|"
    r"important\s*document|statement)$",
    re.IGNORECASE,
)
RECEIPT_NUMBER_RE = re.compile(
    r"(?:receipt|invoice)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})",
    re.IGNORECASE,
)
MERCHANT_RE = re.compile(
    r"(?:merchant|store|sold\s*by|seller)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
PAYMENT_METHOD_RE = re.compile(
    r"payment\s*method\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
# Item 1: 27-inch Monitor — Qty 1 — ₹24,000  (₹ may OCR as I)
RECEIPT_ITEM_RE = re.compile(
    r"Item\s*\d+\s*:\s*(.+?)\s*[—\-–]\s*Qty\.?\s*(\d+)\s*[—\-–]\s*"
    + CURRENCY_PREFIX
    + r"?\s*"
    + AMOUNT_NUMBER
    + r"(?:\s*each)?",
    re.IGNORECASE,
)
SERIAL_RE = re.compile(
    r"(?:serial|s\/n|sn)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-]{3,})",
    re.IGNORECASE,
)
MODEL_RE = re.compile(
    r"(?:model(?:\s*(?:no\.?|number|#))?)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{2,})",
    re.IGNORECASE,
)
PRODUCT_RE = re.compile(
    r"(?:product(?:\s*name)?)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
BRAND_RE = re.compile(
    r"(?:brand|make)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
WARRANTY_PROVIDER_RE = re.compile(
    r"(?:warranty\s*provider|service\s*provider|provider)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
WARRANTY_DURATION_RE = re.compile(
    r"(?:warranty\s*)?(?:duration|period|valid\s*for)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
CURRENCY_RE = re.compile(
    r"(₹|\u20b9|\bINR\b|\bUSD\b|\$|\bEUR\b|€|(?<![A-Za-z0-9])[Il1](?=\d))",
    re.IGNORECASE,
)

# Stable machine-readable document types (DOC-005).
DOCUMENT_TYPE_IDS = (
    "utility_bill",
    "insurance",
    "car_insurance",
    "health_insurance",
    "purchase_receipt",
    "warranty",
    "generic",
)

# Legacy display labels still accepted by the review UI / older clients.
DOCUMENT_TYPE_LABELS = {
    "utility_bill": "Bill",
    "insurance": "Insurance",
    "car_insurance": "Car Insurance",
    "health_insurance": "Health Insurance",
    "purchase_receipt": "Purchase",
    "warranty": "Warranty",
    "generic": "Important document",
}

# Subtypes that share the insurance extraction schema.
INSURANCE_TYPE_IDS = frozenset({"insurance", "car_insurance", "health_insurance"})

# Accepted values for update_extraction (ids + display labels).
DOCUMENT_TYPES = DOCUMENT_TYPE_IDS + tuple(DOCUMENT_TYPE_LABELS.values()) + ("Other",)

OCR_DPI = 220
_ocr = None


def display_document_type(doc_type: str) -> str:
    """Map machine id (or legacy label) to the frontend display label."""
    key = normalize_document_type(doc_type)
    if (doc_type or "").strip() == "Other":
        return "Other"
    return DOCUMENT_TYPE_LABELS.get(key, doc_type or DOCUMENT_TYPE_LABELS["generic"])


def normalize_document_type(value: str | None) -> str:
    """Normalize free-text / legacy labels to a stable DOCUMENT_TYPE_ID."""
    text = (value or "").strip()
    if not text:
        return "generic"
    if text == "Other":
        return "generic"
    lowered = text.lower().replace("-", "_").replace(" ", "_")
    if lowered in DOCUMENT_TYPE_IDS:
        return lowered
    # Exact legacy label match first (e.g. "Car Insurance").
    for type_id, label in DOCUMENT_TYPE_LABELS.items():
        if text == label or lowered == label.lower().replace(" ", "_").replace("-", "_"):
            return type_id
    # Insurance subtypes before generic insurance.
    if "health" in lowered or "medical" in lowered or "hospital" in lowered or "hlth" in lowered:
        if "insurance" in lowered or "policy" in lowered:
            return "health_insurance"
    if any(token in lowered for token in ("car", "motor", "auto", "vehicle", "four_wheeler", "two_wheeler")):
        if "insurance" in lowered or "policy" in lowered:
            return "car_insurance"
    if "insurance" in lowered or ("policy" in lowered and "warranty" not in lowered):
        return "insurance"
    if "warranty" in lowered:
        return "warranty"
    if "purchase" in lowered or "receipt" in lowered or "invoice" in lowered:
        return "purchase_receipt"
    if "utility" in lowered or lowered == "bill" or "bill" in lowered:
        return "utility_bill"
    if "important" in lowered or "generic" in lowered or lowered == "other":
        return "generic"
    return "generic"


def schema_document_type(doc_type: str) -> str:
    """Map subtype ids to the Pydantic schema / field set they share."""
    type_id = normalize_document_type(doc_type)
    if type_id in INSURANCE_TYPE_IDS:
        return "insurance"
    return type_id


def classify_document(text: str) -> str:
    lowered = text.lower()
    if "insurance" in lowered or "policy" in lowered or "premium" in lowered:
        if any(token in lowered for token in ("health", "medical", "hospital", "hlth")):
            return "health_insurance"
        if any(
            token in lowered
            for token in ("car", "motor", "auto", "vehicle", "four wheeler", "two wheeler")
        ):
            return "car_insurance"
        return "insurance"
    if "warranty" in lowered:
        return "warranty"
    if "invoice" in lowered or "receipt" in lowered:
        return "purchase_receipt"
    if "bill" in lowered or "due date" in lowered or "amount due" in lowered:
        return "utility_bill"
    return "generic"


def _ocr_engine():
    global _ocr
    if _ocr is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            from rapidocr import RapidOCR

        _ocr = RapidOCR()
    return _ocr



def inspect_pdf(path: Path) -> tuple[int, bool]:
    document = pymupdf.open(path)
    try:
        encrypted = bool(getattr(document, "is_encrypted", False))
        if encrypted and not document.authenticate(""):
            return int(document.page_count), True
        return int(document.page_count), False
    finally:
        document.close()


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    document = pymupdf.open(path)
    try:
        if getattr(document, "is_encrypted", False) and not document.authenticate(""):
            raise ValueError("This PDF is password protected.")
        return [(index, page.get_text() or "") for index, page in enumerate(document, start=1)]
    finally:
        document.close()


def ocr_image(path: Path) -> str:
    output = _ocr_engine()(str(path))
    result = output[0] if isinstance(output, tuple) else output
    if result is None:
        return ""
    texts = getattr(result, "txts", None)
    if texts:
        return "\n".join(str(line) for line in texts if line)
    lines: list[str] = []
    for item in result:
        if isinstance(item, str):
            lines.append(item)
        elif isinstance(item, (list, tuple)) and len(item) > 1:
            lines.append(str(item[1]))
    return "\n".join(lines)


def ocr_pdf_pages(path: Path) -> list[tuple[int, str]]:
    document = pymupdf.open(path)
    parts: list[tuple[int, str]] = []
    try:
        for index, page in enumerate(document, start=1):
            pix = page.get_pixmap(dpi=OCR_DPI)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            tmp_path = Path(tmp.name)
            try:
                pix.save(str(tmp_path))
                parts.append((index, ocr_image(tmp_path)))
            finally:
                tmp_path.unlink(missing_ok=True)
    finally:
        document.close()
    return parts


def read_document_pages(path: Path, is_pdf: bool) -> list[tuple[int, str]]:
    if not is_pdf:
        return [(1, ocr_image(path))]
    pages = extract_pdf_pages(path)
    text = "\n".join(part for _, part in pages)
    if len(text.strip()) < 40:
        return ocr_pdf_pages(path)
    return pages


def _amount_hit(raw_match: str, confidence: float, evidence: str, page: int) -> FieldHit:
    """Build an amount FieldHit with INR-spaced raw and numeric normalized value."""
    display_raw = canonicalize_amount_raw(raw_match)
    return FieldHit(display_raw, normalize_amount(display_raw or raw_match), confidence, evidence[:200], page)


def _date_near(pages: list[tuple[int, str]], labels: tuple[str, ...]) -> FieldHit:
    for label in labels:
        for page_number, text in pages:
            match = re.search(label + r".{0,60}", text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            found = DATE_TOKEN.search(match.group(0))
            if found:
                raw = found.group(1)
                return FieldHit(raw, normalize_date(raw), 0.75, match.group(0)[:200], page_number)
    return empty_field()


def _amount_near(pages: list[tuple[int, str]], labels: tuple[str, ...]) -> FieldHit:
    for label in labels:
        for page_number, text in pages:
            match = re.search(label + r".{0,80}", text, flags=re.IGNORECASE | re.DOTALL)
            if not match:
                continue
            found = AMOUNT_RE.search(match.group(0))
            if found:
                return _amount_hit(found.group(0).strip(), 0.8, match.group(0), page_number)
    return empty_field()


def _text_near(pages: list[tuple[int, str]], labels: tuple[str, ...], group: int = 1) -> FieldHit:
    for label in labels:
        pattern = re.compile(
            label + r"\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9\-\/\s,]{1,80})",
            re.IGNORECASE,
        )
        for page_number, text in pages:
            found = pattern.search(text)
            if found:
                raw = found.group(group).strip().splitlines()[0][:120]
                return FieldHit(raw, raw, 0.65, found.group(0)[:200], page_number)
    return empty_field()


def _first_match(pages: list[tuple[int, str]], pattern: re.Pattern[str]) -> tuple[re.Match[str] | None, int]:
    for page_number, text in pages:
        found = pattern.search(text)
        if found:
            return found, page_number
    return None, 1


def _guess_provider(pages: list[tuple[int, str]], hint: str | None = None) -> FieldHit:
    """Pick an organization name — never the document title/heading."""
    labeled = _text_near(
        pages,
        (
            "provider",
            "company name",
            "issued by",
            "service provider",
            "utility provider",
            "supplier",
        ),
    )
    if labeled.raw and not PROVIDER_TITLE_RE.match(labeled.raw.strip()):
        return labeled

    lines: list[tuple[str, int]] = []
    for page_number, page_text in pages[:2]:
        for line in page_text.splitlines()[:15]:
            stripped = line.strip()
            if stripped:
                lines.append((stripped, page_number))
    if not lines:
        return empty_field()

    if hint:
        for stripped, page_number in lines:
            if hint in stripped.lower() and len(stripped) < 90 and not PROVIDER_TITLE_RE.match(stripped):
                return FieldHit(stripped[:120], stripped[:120], 0.7, stripped[:200], page_number)

    for stripped, page_number in lines:
        if PROVIDER_TITLE_RE.match(stripped):
            continue
        if re.match(r"^(bill|invoice|receipt|policy|account|customer|due|amount|service)\b", stripped, re.I):
            continue
        if DATE_TOKEN.search(stripped) and len(stripped) < 40:
            continue
        if len(stripped) < 3 or len(stripped) > 120:
            continue
        # Prefer multi-word org-like lines (e.g. "Bengaluru Power & Light Services").
        word_count = len(stripped.split())
        if word_count >= 2 or "&" in stripped or re.search(r"\b(ltd|llc|inc|services|corp|company)\b", stripped, re.I):
            return FieldHit(stripped[:120], stripped[:120], 0.75, stripped[:200], page_number)

    # Last resort: first non-title line.
    for stripped, page_number in lines:
        if not PROVIDER_TITLE_RE.match(stripped):
            return FieldHit(stripped[:120], stripped[:120], 0.45, stripped[:200], page_number)
    return empty_field()


def _guess_currency(pages: list[tuple[int, str]]) -> FieldHit:
    match, page = _first_match(pages, CURRENCY_RE)
    if match:
        raw = match.group(0)
        token = raw.upper()
        if token in ("₹", "RS", "RS.", "INR") or re.fullmatch(r"[IL1]", raw, flags=re.IGNORECASE):
            return FieldHit("INR", "INR", 0.75, match.group(0), page)
        if token in ("$", "USD"):
            return FieldHit(raw, "USD", 0.7, match.group(0), page)
        if token in ("€", "EUR"):
            return FieldHit(raw, "EUR", 0.7, match.group(0), page)
        normalized = token.replace("₹", "INR")
        return FieldHit(raw, normalized, 0.7, match.group(0), page)
    # Fallback: amount lines that used an OCR rupee prefix imply INR.
    amount_match, amount_page = _first_match(pages, AMOUNT_RE)
    if amount_match and _RUPEE_LIKE_PREFIX_RE.search(amount_match.group(0)):
        return FieldHit("INR", "INR", 0.65, amount_match.group(0)[:200], amount_page)
    return empty_field()


def _dated_fallback(pages: list[tuple[int, str]]) -> list[FieldHit]:
    dated: list[FieldHit] = []
    for page_number, page_text in pages:
        for item in DATE_TOKEN.findall(page_text):
            raw = item[0] if isinstance(item, tuple) else item
            dated.append(FieldHit(raw, normalize_date(raw), 0.55, raw, page_number))
    return dated


def extract_utility_bill(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    bill_match, bill_page = _first_match(pages, BILL_NUMBER_RE)
    bill_number = (
        FieldHit(bill_match.group(1), bill_match.group(1), 0.85, bill_match.group(0)[:200], bill_page)
        if bill_match
        else empty_field()
    )

    cust_match, cust_page = _first_match(pages, CUSTOMER_ID_RE)
    customer_id = (
        FieldHit(cust_match.group(1), cust_match.group(1), 0.85, cust_match.group(0)[:200], cust_page)
        if cust_match
        else empty_field()
    )

    period_start = empty_field()
    period_end = empty_field()
    range_match, range_page = _first_match(pages, BILLING_PERIOD_RANGE_RE)
    if range_match:
        start_raw = range_match.group(1).strip()
        end_raw = range_match.group(2).strip()
        period_start = FieldHit(start_raw, normalize_date(start_raw), 0.9, range_match.group(0)[:200], range_page)
        period_end = FieldHit(end_raw, normalize_date(end_raw), 0.9, range_match.group(0)[:200], range_page)
    else:
        period_start = _date_near(
            pages,
            ("billing period start", "period from", "from date", "service from"),
        )
        period_end = _date_near(
            pages,
            ("billing period end", "period to", "to date", "service to"),
        )

    due = _date_near(pages, ("due date", "payment due", "pay by", "due on"))
    amount_due = _amount_near(pages, ("amount due", "total due", "balance due", "amount payable"))
    # Do not invent amount from any random currency figure on the page.

    addr_match, addr_page = _first_match(pages, SERVICE_ADDRESS_RE)
    service_address = empty_field()
    if addr_match:
        raw = addr_match.group(1).strip().splitlines()[0][:200]
        service_address = FieldHit(raw, raw, 0.8, addr_match.group(0)[:200], addr_page)

    previous = _amount_near(pages, ("previous balance", "prior balance", "last balance"))
    current = _amount_near(pages, ("current charges", "current bill", "this period"))

    return {
        "provider": _guess_provider(pages),
        "bill_number": bill_number,
        "customer_id": customer_id,
        "account_number": empty_field(),  # distinct from bill_number; unknown unless labeled
        "billing_period_start": period_start,
        "billing_period_end": period_end,
        "due_date": due,
        "amount_due": amount_due,
        "service_address": service_address,
        "previous_balance": previous,
        "current_charges": current,
        "currency": _guess_currency(pages),
    }


def extract_insurance(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    id_match, id_page = _first_match(pages, POLICY_RE)
    policy = (
        FieldHit(
            id_match.group(1),
            id_match.group(1),
            0.75,
            id_match.group(0)[:200],
            id_page,
        )
        if id_match
        else empty_field()
    )
    effective = _date_near(
        pages,
        (
            "policy start",
            "effective date",
            "start date",
            "commencement",
            "valid from",
            "period of insurance",
            "policy period",
        ),
    )
    expiry = _date_near(
        pages,
        (
            "policy expiry",
            "expiry date",
            "end date",
            "renewal due",
            "valid till",
            "valid until",
            "expires",
        ),
    )
    dated = _dated_fallback(pages)
    if not effective.raw and dated:
        effective = dated[0]
    if not expiry.raw and dated:
        expiry = dated[-1] if len(dated) > 1 else dated[0]
    premium = _amount_near(pages, ("premium", "total premium", "amount payable"))
    if not premium.raw:
        amount_match, amount_page = _first_match(pages, AMOUNT_RE)
        if amount_match:
            premium = _amount_hit(amount_match.group(0).strip(), 0.55, amount_match.group(0), amount_page)
    return {
        "provider": _guess_provider(pages, hint="insurance"),
        "policy_number": policy,
        "policy_holder": _text_near(pages, ("policy holder", "insured", "insured name", "name of insured")),
        "effective_date": effective,
        "expiry_date": expiry,
        "premium": premium,
        "deductible": _amount_near(pages, ("deductible", "excess")),
        "coverage": _text_near(pages, ("coverage", "sum insured", "cover type")),
        "currency": _guess_currency(pages),
    }


def _extract_receipt_items(pages: list[tuple[int, str]]) -> list[dict]:
    """Parse line items into ExtractedValue-shaped dicts (never invents items)."""
    items: list[dict] = []
    for page_number, text in pages:
        for match in RECEIPT_ITEM_RE.finditer(text):
            name_raw = match.group(1).strip()
            qty_raw = match.group(2).strip()
            amount_raw = match.group(3).strip()
            # Full match tail may include OCR "I" prefix — prefer that for display.
            amount_match = AMOUNT_RE.search(match.group(0))
            amount_source = amount_match.group(0).strip() if amount_match else amount_raw
            display_raw = canonicalize_amount_raw(amount_source)
            amount_norm = normalize_amount(display_raw)
            snippet = match.group(0)[:200]
            items.append(
                {
                    "name": {
                        "raw": name_raw,
                        "normalized": name_raw,
                        "confidence": 0.85,
                        "evidence": [{"page_number": page_number, "snippet": snippet}],
                    },
                    "quantity": {
                        "raw": qty_raw,
                        "normalized": qty_raw,
                        "confidence": 0.85,
                        "evidence": [{"page_number": page_number, "snippet": snippet}],
                    },
                    "amount": {
                        "raw": display_raw,
                        "normalized": amount_norm,
                        "confidence": 0.85,
                        "evidence": [{"page_number": page_number, "snippet": snippet}],
                    },
                    "unit_price": {
                        "raw": display_raw,
                        "normalized": amount_norm,
                        "confidence": 0.85,
                        "evidence": [{"page_number": page_number, "snippet": snippet}],
                    },
                    "total": None,
                }
            )
    return items


def _exact_label_amount(pages: list[tuple[int, str]], labels: tuple[str, ...]) -> FieldHit:
    """
    Match amount on a labeled line (or the next non-empty line for table layouts).

    Tolerates OCR where ₹ is rendered as I/l/1 immediately before digits.
    Avoids matching 'Subtotal' when searching for 'Total'.
    """
    for label in labels:
        same_line = re.compile(
            rf"(?m)^[ \t]*{label}[ \t]*[:\-]?[ \t]*(.*?)\s*$",
            re.IGNORECASE,
        )
        label_only = re.compile(
            rf"(?m)^[ \t]*{label}[ \t]*[:\-]?\s*$",
            re.IGNORECASE,
        )
        for page_number, text in pages:
            lines = text.splitlines()
            for index, line in enumerate(lines):
                found = same_line.match(line)
                if found:
                    tail = found.group(1).strip()
                    amount = AMOUNT_RE.search(tail) if tail else None
                    if amount:
                        return _amount_hit(amount.group(0).strip(), 0.9, line.strip(), page_number)
                    # Table layout: label on this line, amount on the next non-empty line.
                    for next_line in lines[index + 1 : index + 4]:
                        candidate = next_line.strip()
                        if not candidate:
                            continue
                        amount = AMOUNT_RE.search(candidate)
                        if amount:
                            snippet = f"{line.strip()} {candidate}"
                            return _amount_hit(amount.group(0).strip(), 0.88, snippet, page_number)
                        break
                elif label_only.match(line):
                    for next_line in lines[index + 1 : index + 4]:
                        candidate = next_line.strip()
                        if not candidate:
                            continue
                        amount = AMOUNT_RE.search(candidate)
                        if amount:
                            snippet = f"{line.strip()} {candidate}"
                            return _amount_hit(amount.group(0).strip(), 0.88, snippet, page_number)
                        break
    return empty_field()


def extract_purchase_receipt(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    merchant = empty_field()
    merchant_match, merchant_page = _first_match(pages, MERCHANT_RE)
    if merchant_match:
        raw = merchant_match.group(1).strip().splitlines()[0][:120]
        if raw and not PROVIDER_TITLE_RE.match(raw):
            merchant = FieldHit(raw, raw, 0.9, merchant_match.group(0)[:200], merchant_page)
    if not merchant.raw:
        merchant = _guess_provider(pages)

    receipt_match, receipt_page = _first_match(pages, RECEIPT_NUMBER_RE)
    receipt_number = (
        FieldHit(
            receipt_match.group(1),
            receipt_match.group(1),
            0.9,
            receipt_match.group(0)[:200],
            receipt_page,
        )
        if receipt_match
        else empty_field()
    )

    purchase_date = _date_near(
        pages,
        ("purchase date", "transaction date", "date of purchase", "invoice date", "receipt date"),
    )
    # Do not invent a date from unrelated tokens if labeled date is missing.

    subtotal = _exact_label_amount(pages, ("subtotal", "sub total", "sub-total"))
    tax = _exact_label_amount(pages, ("tax", "gst", "vat"))
    total = _exact_label_amount(pages, ("grand total", "amount paid", "total due", "total"))
    # Prefer true Total over Subtotal: if total matched the same as subtotal line, retry.
    if total.raw and subtotal.raw and total.normalized == subtotal.normalized and total.evidence == subtotal.evidence:
        total = _exact_label_amount(pages, ("grand total", "amount paid", "total due"))

    payment = empty_field()
    pay_match, pay_page = _first_match(pages, PAYMENT_METHOD_RE)
    if pay_match:
        raw = pay_match.group(1).strip().splitlines()[0][:80]
        payment = FieldHit(raw, raw, 0.85, pay_match.group(0)[:200], pay_page)

    items = _extract_receipt_items(pages)
    if items:
        items_json = json.dumps(items, ensure_ascii=False)
        items_hit = FieldHit(items_json, items_json, 0.85, f"{len(items)} items", items[0]["name"]["evidence"][0]["page_number"])
    else:
        items_hit = empty_field()

    return {
        "merchant": merchant,
        "receipt_number": receipt_number,
        "purchase_date": purchase_date,
        "transaction_date": purchase_date,  # alias for older schema consumers
        "items": items_hit,
        "subtotal": subtotal,
        "tax": tax,
        "discount": _exact_label_amount(pages, ("discount", "promo", "coupon")),
        "total": total,
        "payment_method": payment,
        "currency": _guess_currency(pages),
    }


def extract_warranty(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    def labeled(pattern: re.Pattern[str], *, confidence: float = 0.85) -> FieldHit:
        match, page = _first_match(pages, pattern)
        if not match:
            return empty_field()
        raw = match.group(1).strip().splitlines()[0][:160]
        if not raw or PROVIDER_TITLE_RE.match(raw):
            return empty_field()
        return FieldHit(raw, raw, confidence, match.group(0)[:200], page)

    product = labeled(PRODUCT_RE, confidence=0.9)
    brand = labeled(BRAND_RE, confidence=0.9)

    model_match, model_page = _first_match(pages, MODEL_RE)
    model = (
        FieldHit(model_match.group(1), model_match.group(1), 0.9, model_match.group(0)[:200], model_page)
        if model_match
        else empty_field()
    )

    serial_match, serial_page = _first_match(pages, SERIAL_RE)
    serial = (
        FieldHit(serial_match.group(1), serial_match.group(1), 0.9, serial_match.group(0)[:200], serial_page)
        if serial_match
        else empty_field()
    )

    warranty_provider = labeled(WARRANTY_PROVIDER_RE, confidence=0.9)
    if not warranty_provider.raw:
        # Prefer org-like lines; never invent from document title alone.
        warranty_provider = _guess_provider(pages)

    purchase = _date_near(pages, ("purchase date", "date of purchase", "bought on"))
    start = _date_near(pages, ("warranty start", "warranty from", "coverage start", "valid from"))
    expiry = _date_near(
        pages,
        ("warranty expiry", "warranty end", "warranty until", "valid till", "valid until", "expires on", "expires"),
    )
    # Do not invent warranty dates from unrelated tokens when labels are missing.

    duration = labeled(WARRANTY_DURATION_RE, confidence=0.85)
    if duration.raw:
        # Keep a short duration token (e.g. "24 months").
        duration = FieldHit(
            duration.raw[:80],
            duration.raw[:80],
            duration.confidence,
            duration.evidence,
            duration.page,
        )

    return {
        "product": product,
        "brand": brand,
        "model": model,
        "serial_number": serial,
        "warranty_provider": warranty_provider,
        "purchase_date": purchase,
        "warranty_start": start,
        "warranty_expiry": expiry,
        "warranty_duration": duration,
    }


def extract_generic(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    dated = _dated_fallback(pages)
    doc_date = dated[0] if dated else empty_field()
    title = empty_field()
    for page_number, page_text in pages[:1]:
        for line in page_text.splitlines()[:5]:
            stripped = line.strip()
            if len(stripped) > 3:
                title = FieldHit(stripped[:120], stripped[:120], 0.5, stripped[:200], page_number)
                break
    return {
        "provider": _guess_provider(pages),
        "title": title,
        "document_date": doc_date,
        "key_values": empty_field(),  # unknown complex field — not fabricated
    }


def _legacy_aliases(doc_type: str, fields: dict[str, FieldHit]) -> dict[str, FieldHit]:
    """
    Flat frontend / actions aliases for types that still use the shared review form.

    utility_bill intentionally does NOT alias into policyNumber / startDate /
    expiryDate / premium — those insurance-shaped names must not appear for bills.
    """

    def pick(*names: str) -> FieldHit:
        for name in names:
            hit = fields.get(name)
            if hit and (hit.raw or hit.normalized):
                return hit
        return empty_field()

    if doc_type == "utility_bill":
        # Keep provider only; leave insurance-shaped legacy keys empty/absent.
        return {}
    if doc_type == "purchase_receipt":
        # Do not alias merchant/receipt/date/total into insurance-shaped flat fields.
        return {}
    if doc_type == "warranty":
        # Do not alias serial/dates into policyNumber / startDate / expiryDate / premium.
        return {}
    if doc_type in INSURANCE_TYPE_IDS:
        return {
            "provider": pick("provider"),
            "policyNumber": pick("policy_number"),
            "startDate": pick("effective_date"),
            "expiryDate": pick("expiry_date"),
            "premium": pick("premium"),
        }
    return {
        "provider": pick("provider"),
        "policyNumber": empty_field(),
        "startDate": pick("document_date"),
        "expiryDate": pick("document_date"),
        "premium": empty_field(),
    }


def field_hit_to_value_dict(hit: FieldHit | None) -> dict | None:
    """Convert a FieldHit to ExtractedValue-shaped dict, or None if unknown."""
    if hit is None:
        return None
    if not (hit.raw or hit.normalized):
        return None
    evidence = []
    if hit.evidence:
        evidence.append({"page_number": hit.page or 1, "snippet": hit.evidence[:200]})
    return {
        "raw": hit.raw or None,
        "normalized": hit.normalized or None,
        "confidence": hit.confidence if hit.raw or hit.normalized else None,
        "evidence": evidence,
    }


TYPE_SPECIFIC_FIELD_NAMES: dict[str, tuple[str, ...]] = {
    "utility_bill": (
        "provider",
        "bill_number",
        "customer_id",
        "account_number",
        "billing_period_start",
        "billing_period_end",
        "due_date",
        "amount_due",
        "service_address",
        "previous_balance",
        "current_charges",
        "currency",
    ),
    "insurance": (
        "provider",
        "policy_number",
        "policy_holder",
        "effective_date",
        "expiry_date",
        "premium",
        "deductible",
        "coverage",
        "currency",
    ),
    "purchase_receipt": (
        "merchant",
        "receipt_number",
        "purchase_date",
        "transaction_date",
        "items",
        "subtotal",
        "tax",
        "discount",
        "total",
        "payment_method",
        "currency",
    ),
    "warranty": (
        "product",
        "brand",
        "model",
        "serial_number",
        "warranty_provider",
        "purchase_date",
        "warranty_start",
        "warranty_expiry",
        "warranty_duration",
    ),
    "generic": ("provider", "title", "document_date", "key_values"),
}


COMPLEX_JSON_FIELDS = frozenset({"items", "key_values"})


def build_structured_payload(doc_type: str, fields: dict[str, FieldHit]) -> dict:
    """Build a type-specific structured extraction dict for validation / API."""
    type_id = normalize_document_type(doc_type)
    schema_type = schema_document_type(type_id)
    doc_hit = fields.get("documentType") or FieldHit(type_id, type_id, 0.7, "", 1)
    payload: dict = {
        "document_type": field_hit_to_value_dict(doc_hit)
        or {"raw": type_id, "normalized": type_id, "confidence": 0.7, "evidence": []},
    }
    for name in TYPE_SPECIFIC_FIELD_NAMES.get(schema_type, ()):
        hit = fields.get(name)
        if name in COMPLEX_JSON_FIELDS:
            # Unknown / empty complex fields stay null — do not invent structure.
            if hit and hit.raw:
                try:
                    payload[name] = json.loads(hit.raw)
                except (json.JSONDecodeError, TypeError):
                    payload[name] = None
            else:
                payload[name] = None
        else:
            payload[name] = field_hit_to_value_dict(hit)
    return payload


def guess_fields(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    text = "\n".join(part for _, part in pages)
    doc_type = classify_document(text)

    if doc_type == "utility_bill":
        typed = extract_utility_bill(pages)
    elif doc_type in INSURANCE_TYPE_IDS:
        typed = extract_insurance(pages)
    elif doc_type == "purchase_receipt":
        typed = extract_purchase_receipt(pages)
    elif doc_type == "warranty":
        typed = extract_warranty(pages)
    else:
        typed = extract_generic(pages)

    fields: dict[str, FieldHit] = dict(typed)
    fields["documentType"] = FieldHit(doc_type, doc_type, 0.7 if text.strip() else 0.2, "", 1)
    # Do not invent insurance-shaped flat fields for utility bills.
    aliases = _legacy_aliases(doc_type, fields)
    if aliases:
        fields.update(aliases)
    return fields
