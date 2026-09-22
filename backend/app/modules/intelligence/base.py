from typing import Protocol

from ..documents.text import FieldHit
from .types import IntelligenceResult, NormalizedDocument, PurposeDecision


class IntelligenceError(Exception):
    """Raised when an AI provider cannot complete analysis."""


class DocumentIntelligenceProvider(Protocol):
    supports_native_files: bool

    def classify(self, document: NormalizedDocument) -> PurposeDecision: ...

    def extract(self, document: NormalizedDocument, document_type: str) -> dict[str, FieldHit]: ...

    def analyze(
        self,
        document: NormalizedDocument,
        *,
        file_bytes: bytes | None = None,
        mime_type: str | None = None,
    ) -> IntelligenceResult: ...
