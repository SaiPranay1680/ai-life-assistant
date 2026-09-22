import logging

from .base import DocumentIntelligenceProvider
from .local import LocalIntelligenceProvider

logger = logging.getLogger(__name__)

_provider: DocumentIntelligenceProvider | None = None


def reset_provider() -> None:
    global _provider
    _provider = None


def build_provider() -> DocumentIntelligenceProvider:
    from ...core.config import settings

    name = (settings.ai_provider or "gemini").strip().lower()
    if name == "gemini" and (settings.gemini_api_key or "").strip():
        try:
            from .gemini import GeminiIntelligenceProvider

            return GeminiIntelligenceProvider()
        except Exception:
            logger.exception("Gemini intelligence is unavailable; using the local extractor.")
    return LocalIntelligenceProvider()


def get_provider() -> DocumentIntelligenceProvider:
    global _provider
    if _provider is None:
        _provider = build_provider()
    return _provider
