import re

from ..documents.text import DATE_TOKEN, FieldHit, empty_field, find_amount_match, normalize_amount, normalize_date
from .important import humanize_label, important_keys_for
from .schemas import SCHEMA_FIELDS
from .types import (
    INVALID_DOCUMENT_REASON,
    UNCLEAR_DOCUMENT_REASON,
    IntelligenceResult,
    NormalizedDocument,
    PurposeDecision,
)

LOREM_MARKERS = ("lorem ipsum", "consectetur adipiscing", "dolor sit amet")
PUBLICATION_MARKERS = ("newspaper", "classified ads", "sports desk", "editorial", "volume no", "issue no")
PHOTO_TEXT_LIMIT = 40

UNKNOWN_MARKERS = (
    "assignment",
    "project plan",
    "project proposal",
    "course code",
    "submission date",
    "lecture notes",
    "admission letter",
    "offer letter",
    "curriculum vitae",
    "resume",
    "research paper",
    "company overview",
    "our services",
    "wedding invitation",
)

CATEGORY_SIGNALS: dict[str, tuple[str, ...]] = {
    "Insurance": (
        "insurance",
        "policy number",
        "policy no",
        "sum insured",
        "sum assured",
        "premium",
        "idv",
        "insurer",
    ),
    "Bill": (
        "amount due",
        "amount payable",
        "electricity",
        "bescom",
        "consumer number",
        "units consumed",
        "broadband",
        "mobile bill",
        "postpaid",
        "credit card statement",
        "due date",
        "due:",
    ),
    "Purchase": ("invoice", "tax invoice", "receipt", "order id", "gstin", "sold by"),
    "Warranty": ("warranty", "guarantee period", "warranty card"),
    "Important document": ("passport", "driving licence", "driving license", "aadhaar", "pan card"),
}

ID_RE = re.compile(r"[A-Z0-9][A-Z0-9\-\/]{4,}")


def _score(text: str, phrases: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for phrase in phrases if phrase in lowered)


def classify_document(document: NormalizedDocument) -> PurposeDecision:
    text = document.text
    lowered = text.lower()
    stripped = text.strip()

    if document.page_count > 30:
        return PurposeDecision(
            status="rejected",
            document_type="Other",
            category="publication",
            subtype="too_many_pages",
            reason=INVALID_DOCUMENT_REASON,
            confidence=0.95,
        )
    if any(marker in lowered for marker in LOREM_MARKERS):
        return PurposeDecision(
            status="not_useful",
            document_type="Other",
            category="other",
            subtype="placeholder",
            reason=INVALID_DOCUMENT_REASON,
            confidence=0.99,
        )
    if any(marker in lowered for marker in PUBLICATION_MARKERS) and _score(lowered, CATEGORY_SIGNALS["Insurance"] + CATEGORY_SIGNALS["Bill"]) < 2:
        return PurposeDecision(
            status="rejected",
            document_type="Other",
            category="publication",
            subtype="newspaper",
            reason=INVALID_DOCUMENT_REASON,
            confidence=0.9,
        )
    if document.is_image and len(stripped) < PHOTO_TEXT_LIMIT:
        return PurposeDecision(
            status="rejected",
            document_type="Other",
            category="photo",
            subtype="natural_photo",
            reason=INVALID_DOCUMENT_REASON,
            confidence=0.92,
        )
    if len(stripped) < 8:
        return PurposeDecision(
            status="not_useful",
            document_type="Other",
            category="other",
            subtype="empty",
            reason=INVALID_DOCUMENT_REASON,
            confidence=0.9,
        )

    unknown_hits = _score(lowered, UNKNOWN_MARKERS)
    scored = {name: _score(lowered, phrases) for name, phrases in CATEGORY_SIGNALS.items()}
    best_type, best_score = max(scored.items(), key=lambda item: item[1])

    if unknown_hits and best_score < 2:
        subtype = next((marker.replace(" ", "_") for marker in UNKNOWN_MARKERS if marker in lowered), "other")
        return PurposeDecision(
            status="unknown",
            document_type="Other",
            category="other",
            subtype=subtype,
            reason=UNCLEAR_DOCUMENT_REASON,
            confidence=0.84,
        )
    if best_score >= 2:
        return PurposeDecision(
            status="supported",
            document_type=best_type,
            category=best_type.lower().replace(" ", "_"),
            subtype=best_type.lower().replace(" ", "_"),
            reason=f"{best_type} identified.",
            confidence=min(0.7 + 0.08 * best_score, 0.97),
        )
    if best_score == 1:
        return PurposeDecision(
            status="unknown",
            document_type="Other",
            category="other",
            subtype="unclear",
            reason=UNCLEAR_DOCUMENT_REASON,
            confidence=0.55,
        )
    return PurposeDecision(
        status="unknown",
        document_type="Other",
        category="other",
        subtype="unclear",
        reason=UNCLEAR_DOCUMENT_REASON,
        confidence=0.6,
    )


def _window_after_label(text: str, label: str, span: int = 80) -> list[str]:
    windows: list[str] = []
    start = 0
    lowered = text.lower()
    needle = label.lower()
    while True:
        index = lowered.find(needle, start)
        if index < 0:
            break
        windows.append(text[index : index + len(label) + span])
        start = index + len(needle)
    return windows


def _hit_from_window(window: str, kind: str, page: int) -> FieldHit | None:
    if kind == "date":
        found = DATE_TOKEN.search(window)
        if not found:
            return None
        raw = found.group(1)
        return FieldHit(raw, normalize_date(raw), 0.86, window.strip()[:200], page)
    if kind == "amount":
        found = find_amount_match(window)
        if not found:
            return None
        raw = found.group(0).strip()
        return FieldHit(raw, normalize_amount(raw), 0.88, window.strip()[:200], page)
    if kind == "id":
        found = ID_RE.search(window)
        if not found:
            return None
        raw = found.group(0).strip()
        return FieldHit(raw, raw, 0.8, window.strip()[:200], page)
    line = " ".join(window.split())[:120]
    if not line:
        return None
    return FieldHit(line, line, 0.6, line[:200], page)


def extract_field(pages: list[tuple[int, str]], spec: dict) -> FieldHit:
    labels: tuple[str, ...] = spec["labels"]
    kind = spec["kind"]
    forbidden: tuple[str, ...] = spec["forbidden"]
    for label in labels:
        for page_number, text in pages:
            line_windows = [line.strip() for line in text.splitlines() if label.lower() in line.lower()]
            char_windows = _window_after_label(text, label, span=40) if not line_windows else []
            for window in line_windows + char_windows:
                lowered = window.lower()
                if any(token in lowered for token in forbidden):
                    continue
                hit = _hit_from_window(window, kind, page_number)
                if hit:
                    return hit
    return empty_field()


def evidence_supports(hit: FieldHit, spec: dict) -> bool:
    if not hit.raw:
        return False
    evidence = (hit.evidence or "").lower()
    if any(token in evidence for token in spec["forbidden"]):
        return False
    return any(label in evidence for label in spec["labels"])


def extract_fields(document: NormalizedDocument, document_type: str) -> dict[str, FieldHit]:
    schema = SCHEMA_FIELDS.get(document_type, SCHEMA_FIELDS["Other"])
    fields: dict[str, FieldHit] = {}
    for name, spec in schema.items():
        hit = extract_field(document.pages, spec)
        if hit.raw and not evidence_supports(hit, spec):
            hit = empty_field()
        fields[name] = hit
    if document_type != "Other":
        title = next((line.strip()[:120] for _, text in document.pages for line in text.splitlines() if line.strip()), "")
        if "provider" in schema and not fields.get("provider", empty_field()).raw and title:
            fields["provider"] = FieldHit(title, title, 0.45, title, document.pages[0][0] if document.pages else 1)
    fields["documentType"] = FieldHit(document_type, document_type, 0.8, "", 1)
    return fields


class LocalIntelligenceProvider:
    supports_native_files = False

    def classify(self, document: NormalizedDocument) -> PurposeDecision:
        return classify_document(document)

    def extract(self, document: NormalizedDocument, document_type: str) -> dict[str, FieldHit]:
        return extract_fields(document, document_type)

    def analyze(
        self,
        document: NormalizedDocument,
        *,
        file_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> IntelligenceResult:
        del file_bytes, mime_type
        decision = self.classify(document)
        schema_name = decision.document_type if decision.status == "supported" else "Other"
        fields = self.extract(document, schema_name)
        important = important_keys_for(schema_name, fields)
        labels = {key: humanize_label(key) for key in important}
        return IntelligenceResult(
            decision=decision,
            fields=fields,
            important_keys=important,
            field_labels=labels,
        )
