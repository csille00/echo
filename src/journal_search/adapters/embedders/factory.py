"""Embedding adapter factory."""

from typing import cast

from journal_search.adapters.embedders.ollama import OllamaEmbedder
from journal_search.config import EmbeddingProvider, Settings
from journal_search.ports.embedder import EmbeddingProvider as EmbeddingPort


def create_embedding_provider(settings: Settings) -> EmbeddingPort:
    """Create the configured embedding adapter."""
    if settings.embedding_provider == EmbeddingProvider.OLLAMA:
        return cast(
            EmbeddingPort,
            OllamaEmbedder(
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
                base_url=settings.ollama_base_url,
            ),
        )

    if settings.embedding_provider == EmbeddingProvider.GOOGLE:
        from journal_search.adapters.embedders.google import GoogleEmbedder

        api_key = (
            settings.google_embedding_api_key.get_secret_value()
            if settings.google_embedding_api_key is not None
            else None
        )
        credentials_file = settings.google_embedding_credentials_file
        if not api_key and not credentials_file:
            raise ValueError(
                "Google embedding credentials required. Set GOOGLE_EMBEDDING_API_KEY, "
                "GOOGLE_EMBEDDING_CREDENTIALS_FILE, or reuse Vision credentials."
            )
        # Prefer an explicit API key (AI Studio) over the Vision service account file.
        if api_key:
            credentials_file = None
        return cast(
            EmbeddingPort,
            GoogleEmbedder(
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
                api_key=api_key,
                credentials_file=credentials_file,
            ),
        )

    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
