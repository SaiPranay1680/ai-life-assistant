from dataclasses import dataclass, field

from ..documents.text import FieldHit

INVALID_DOCUMENT_REASON = "Invalid document. Try uploading another."
UNCLEAR_DOCUMENT_REASON = "Document type is unclear. Keep it or upload another."


def user_facing_reason(status: str, reason: str = "") -> str:
    status = (status or "").strip().lower()
    if status in {"rejected", "not_useful"}:
        return INVALID_DOCUMENT_REASON
    if status == "unknown":
        return UNCLEAR_DOCUMENT_REASON
    return (reason or "").strip()


@dataclass(frozen=True)
class NormalizedDocument:
    pages: list[tuple[int, str]]
    is_pdf: bool
    is_image: bool
    page_count: int
    filename: str

    @property
    def text(self) -> str:
        return "\n".join(part for _, part in self.pages)


@dataclass(frozen=True)
class PurposeDecision:
    status: str
    document_type: str
    category: str
    subtype: str
    reason: str
    confidence: float


@dataclass(frozen=True)
class IntelligenceResult:
    decision: PurposeDecision
    fields: dict[str, FieldHit]
    important_keys: list[str] = field(default_factory=list)
    field_labels: dict[str, str] = field(default_factory=dict)
