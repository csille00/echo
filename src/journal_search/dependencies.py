"""Dependency injection container."""

from contextvars import ContextVar
from typing import cast

from journal_search.adapters.db.repository import EntryRepository
from journal_search.adapters.embedders.ollama import OllamaEmbedder
from journal_search.adapters.ocr.google_vision import GoogleVisionOCR
from journal_search.adapters.ocr.surya import SuryaOCR
from journal_search.adapters.ocr.tesseract import TesseractOCR
from journal_search.adapters.storage.supabase import SupabaseStorage
from journal_search.adapters.text_cleanup.ai_sdk import AISDKTextCleanup
from journal_search.config import Settings
from journal_search.ports.embedder import EmbeddingProvider
from journal_search.ports.ocr import OCRProvider
from journal_search.ports.storage import StorageProvider
from journal_search.ports.text_cleanup import TextCleanupProvider

# Context variables for request-scoped dependencies
_ocr_provider: ContextVar[OCRProvider] = ContextVar("ocr_provider")
_embedding_provider: ContextVar[EmbeddingProvider] = ContextVar("embedding_provider")
_storage_provider: ContextVar[StorageProvider] = ContextVar("storage_provider")
_entry_repository: ContextVar[EntryRepository] = ContextVar("entry_repository")
_text_cleanup_provider: ContextVar[TextCleanupProvider | None] = ContextVar(
    "text_cleanup_provider",
    default=None,
)


def set_ocr(provider: OCRProvider) -> None:
    """Set the OCR provider for the current context."""
    _ocr_provider.set(provider)


def get_ocr() -> OCRProvider:
    """Get the OCR provider for the current context."""
    return _ocr_provider.get()


def set_embedder(provider: EmbeddingProvider) -> None:
    """Set the embedding provider for the current context."""
    _embedding_provider.set(provider)


def get_embedder() -> EmbeddingProvider:
    """Get the embedding provider for the current context."""
    return _embedding_provider.get()


def set_storage(provider: StorageProvider) -> None:
    """Set the storage provider for the current context."""
    _storage_provider.set(provider)


def get_storage() -> StorageProvider:
    """Get the storage provider for the current context."""
    return _storage_provider.get()


def set_repository(repo: EntryRepository) -> None:
    """Set the entry repository for the current context."""
    _entry_repository.set(repo)


def get_repository() -> EntryRepository:
    """Get the entry repository for the current context."""
    return _entry_repository.get()


def set_text_cleanup(provider: TextCleanupProvider | None) -> None:
    """Set the optional text cleanup provider for the current context."""
    _text_cleanup_provider.set(provider)


def get_text_cleanup() -> TextCleanupProvider | None:
    """Get the optional text cleanup provider for the current context."""
    return _text_cleanup_provider.get()


class Container:
    """
    Dependency container for bootstrapping the application.

    This creates and holds singleton instances of adapters
    based on configuration.
    """

    def __init__(
        self,
        ocr: OCRProvider | None = None,
        embedder: EmbeddingProvider | None = None,
        storage: StorageProvider | None = None,
        text_cleanup: TextCleanupProvider | None = None,
    ) -> None:
        self._ocr = ocr
        self._embedder = embedder
        self._storage = storage
        self._text_cleanup = text_cleanup

    @property
    def ocr(self) -> OCRProvider:
        if self._ocr is None:
            raise RuntimeError("OCR provider not configured")
        return self._ocr

    @property
    def embedder(self) -> EmbeddingProvider:
        if self._embedder is None:
            raise RuntimeError("Embedding provider not configured")
        return self._embedder

    @property
    def storage(self) -> StorageProvider:
        if self._storage is None:
            raise RuntimeError("Storage provider not configured")
        return self._storage

    @property
    def text_cleanup(self) -> TextCleanupProvider | None:
        return self._text_cleanup

    def install(self) -> None:
        """Install providers into context variables."""
        if self._ocr:
            set_ocr(self._ocr)
        if self._embedder:
            set_embedder(self._embedder)
        if self._storage:
            set_storage(self._storage)
        set_text_cleanup(self._text_cleanup)

    async def close(self) -> None:
        """Release adapter resources such as HTTP clients and thread pools."""
        if self._ocr is not None and hasattr(self._ocr, "close"):
            await self._ocr.close()
        if self._text_cleanup is not None and hasattr(self._text_cleanup, "close"):
            await self._text_cleanup.close()


def create_ocr_provider(provider_name: str, **kwargs: object) -> OCRProvider:
    """Factory for creating OCR providers."""
    if provider_name == "tesseract":
        return cast(OCRProvider, TesseractOCR(**kwargs))
    if provider_name == "surya":
        return cast(OCRProvider, SuryaOCR(**kwargs))
    if provider_name == "google_vision":
        return cast(OCRProvider, GoogleVisionOCR(**kwargs))
    raise ValueError(f"Unknown OCR provider: {provider_name}")


def create_embedding_provider(provider_name: str, **kwargs: object) -> EmbeddingProvider:
    """Factory for creating embedding providers."""
    if provider_name == "ollama":
        return cast(EmbeddingProvider, OllamaEmbedder(**kwargs))
    raise ValueError(f"Unknown embedding provider: {provider_name}")


def create_text_cleanup_provider(
    provider_name: str,
    *,
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
) -> TextCleanupProvider:
    """Factory for creating text cleanup providers."""
    return AISDKTextCleanup(
        provider=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
    )


def create_ocr_provider_from_settings(settings: Settings) -> OCRProvider:
    """Create an OCR provider from application settings."""
    if settings.ocr_provider.value == "google_vision":
        api_key = (
            settings.google_vision_api_key.get_secret_value()
            if settings.google_vision_api_key is not None
            else None
        )
        credentials_file = settings.google_vision_credentials_file
        if not api_key and not credentials_file:
            raise ValueError(
                "Google Vision credentials required. Set GOOGLE_VISION_API_KEY or "
                "GOOGLE_APPLICATION_CREDENTIALS."
            )
        return create_ocr_provider(
            "google_vision",
            api_key=api_key,
            credentials_file=credentials_file,
        )

    return create_ocr_provider(settings.ocr_provider.value)


def create_embedding_provider_from_settings(settings: Settings) -> EmbeddingProvider:
    """Create an embedding provider from application settings."""
    kwargs: dict[str, object] = {
        "model": settings.embedding_model,
        "dimension": settings.embedding_dimension,
        "base_url": settings.ollama_base_url,
    }
    if settings.embedding_provider.value == "openai":
        if settings.openai_api_key is None:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY.")
        kwargs["api_key"] = settings.openai_api_key.get_secret_value()

    return create_embedding_provider(settings.embedding_provider.value, **kwargs)


def create_text_cleanup_provider_from_settings(
    settings: Settings,
) -> TextCleanupProvider | None:
    """Create a text cleanup provider when enabled in settings."""
    if not settings.llm_cleanup_enabled:
        return None

    provider = settings.llm_provider.value
    kwargs: dict[str, str | None] = {"model": settings.llm_model}

    if provider == "ollama":
        kwargs["base_url"] = settings.ollama_base_url
    elif provider == "openai":
        if settings.openai_api_key is None:
            raise ValueError("OpenAI API key required for LLM cleanup. Set OPENAI_API_KEY.")
        kwargs["api_key"] = settings.openai_api_key.get_secret_value()

    return create_text_cleanup_provider(provider, **kwargs)
