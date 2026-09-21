import re
import tempfile
from pathlib import Path

import pymupdf

from .text import DATE_TOKEN, FieldHit, empty_field, normalize_amount, normalize_date

AMOUNT_RE = re.compile(
    r"(?:₹|\u20b9|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]{1,2})?|[0-9]+\.[0-9]{2})",
    re.IGNORECASE,
)
POLICY_RE = re.compile(
    r"(?:policy|account|invoice|bill)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{4,})",
    re.IGNORECASE,
)
DOCUMENT_TYPES = ("Bill", "Insurance", "Purchase", "Warranty", "Important document", "Other")
OCR_DPI = 220
_ocr = None


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
