"""AI SDK factory."""

from __future__ import annotations

from journal_search.config import LLMProvider, Settings


def create_ai_sdk_from_settings(settings: Settings):
    """Create the app-level AI SDK for Ollama text cleanup."""
    if settings.llm_provider != LLMProvider.OLLAMA:
        return None

    from journal_search.adapters.ai_sdk.client import AISDK

    return AISDK(
        provider="ollama",
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
    )
