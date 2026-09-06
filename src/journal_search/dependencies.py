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
from journal_search.ports.embedder import EmbeddingProvider
from journal_search.ports.ocr import OCRProvider
from journal_search.ports.storage import StorageProvider

# Context variables for request-scoped dependencies
_ocr_provider: ContextVar[OCRProvider] = ContextVar("ocr_provider")
_embedding_provider: ContextVar[EmbeddingProvider] = ContextVar("embedding_provider")
_storage_provider: ContextVar[StorageProvider] = ContextVar("storage_provider")
_entry_repository: ContextVar[EntryRepository] = ContextVar("entry_repository")


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
    ) -> None:
        self._ocr = ocr
        self._embedder = embedder
        self._storage = storage

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

    def install(self) -> None:
        """Install providers into context variables."""
        if self._ocr:
            set_ocr(self._ocr)
        if self._embedder:
            set_embedder(self._embedder)
        if self._storage:
            set_storage(self._storage)


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
    # Add more providers here:
    # elif provider_name == "openai":
    #     from journal_search.adapters.embedders.openai import OpenAIEmbedder
    #     return OpenAIEmbedder(**kwargs)
    raise ValueError(f"Unknown embedding provider: {provider_name}")


def create_text_cleanup_provider(provider_name: str, **kwargs: object) -> object:
    """Factory for creating text cleanup providers."""
    return AISDKTextCleanup(provider=provider_name, **kwargs)
