import re
import tempfile
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pymupdf

AMOUNT_RE = re.compile(
    r"(?:₹|\u20b9|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?|[0-9]+\.[0-9]{2})",
    re.IGNORECASE,
)
DATE_TOKEN = re.compile(
    r"(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?,?\s+\d{2,4}"
    r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
POLICY_RE = re.compile(
    r"(?:policy|account|invoice|bill)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})",
    re.IGNORECASE,
)
DOCUMENT_TYPES = ("Bill", "Insurance", "Purchase", "Warranty", "Important document")
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

_ocr = None


class FieldHit(NamedTuple):
    raw: str
    normalized: str
    confidence: float
    evidence: str
    page: int


def empty_field(page: int = 1) -> FieldHit:
    return FieldHit("", "", 0.0, "", page)


def _ocr_engine():
    global _ocr
    if _ocr is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            from rapidocr import RapidOCR

        _ocr = RapidOCR()
    return _ocr


def extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    document = pymupdf.open(path)
    try:
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
            pix = page.get_pixmap(dpi=140)
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


def classify_document(text: str) -> str:
    lowered = text.lower()
    if "insurance" in lowered or "policy" in lowered or "premium" in lowered:
        return "Insurance"
    if "warranty" in lowered:
        return "Warranty"
    if "invoice" in lowered or "receipt" in lowered:
        return "Purchase"
    if "bill" in lowered or "due date" in lowered or "amount due" in lowered:
        return "Bill"
    return "Important document"


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


def _first_match(pages: list[tuple[int, str]], pattern: re.Pattern[str]) -> tuple[re.Match[str] | None, int]:
    for page_number, text in pages:
        found = pattern.search(text)
        if found:
            return found, page_number
    return None, 1


def guess_fields(pages: list[tuple[int, str]]) -> dict[str, FieldHit]:
    text = "\n".join(part for _, part in pages)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    provider = lines[0][:120] if lines else ""
    provider_page = pages[0][0] if pages else 1
    for page_number, page_text in pages[:2]:
        for line in page_text.splitlines()[:8]:
            stripped = line.strip()
            if "insurance" in stripped.lower() and len(stripped) < 90:
                provider = stripped[:120]
                provider_page = page_number
                break

    amount_match, amount_page = _first_match(pages, AMOUNT_RE)
    policy_match, policy_page = _first_match(pages, POLICY_RE)
    amount = amount_match.group(0).strip() if amount_match else ""
    policy = policy_match.group(1) if policy_match else ""

    start = _date_near(
        pages,
        (
            "policy start",
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
            "due date",
            "expires",
        ),
    )
    if not start.raw or not expiry.raw:
        dated: list[FieldHit] = []
        for page_number, page_text in pages:
            for item in DATE_TOKEN.findall(page_text):
                raw = item[0] if isinstance(item, tuple) else item
                dated.append(FieldHit(raw, normalize_date(raw), 0.7, raw, page_number))
        if not start.raw and dated:
            start = dated[0]
        if not expiry.raw and dated:
            expiry = dated[-1] if len(dated) > 1 else dated[0]

    doc_type = classify_document(text)
    return {
        "provider": FieldHit(provider, provider, 0.6 if provider else 0.0, provider, provider_page),
        "premium": FieldHit(
            amount,
            normalize_amount(amount),
            0.7 if amount else 0.0,
            amount,
            amount_page,
        ),
        "startDate": start,
        "expiryDate": expiry,
        "policyNumber": FieldHit(
            policy,
            policy,
            0.6 if policy else 0.0,
            policy_match.group(0) if policy_match else "",
            policy_page,
        ),
        "documentType": FieldHit(doc_type, doc_type, 0.7 if text.strip() else 0.2, "", 1),
    }
