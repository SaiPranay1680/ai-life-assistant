from .local import LocalIntelligenceProvider

_provider: LocalIntelligenceProvider | None = None


def get_provider() -> LocalIntelligenceProvider:
    global _provider
    if _provider is None:
        _provider = LocalIntelligenceProvider()
    return _provider
