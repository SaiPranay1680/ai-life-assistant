from dataclasses import dataclass


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
