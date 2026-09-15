"""Dependency injection container."""

from typing import cast

from journal_search.adapters.embedders.factory import (
    create_embedding_provider as build_embedding_provider,
)
from journal_search.adapters.ocr.google_vision import GoogleVisionOCR
from journal_search.adapters.ocr.surya import SuryaOCR
from journal_search.adapters.ocr.tesseract import TesseractOCR
from journal_search.adapters.supabase.client import SupabaseClient
from journal_search.adapters.text_cleanup.cleanup import TextCleanup
from journal_search.config import Settings
from journal_search.ports.auth import AuthProvider
from journal_search.ports.embedder import EmbeddingProvider
from journal_search.ports.llm import LLMService
from journal_search.ports.ocr import OCRProvider
from journal_search.ports.realtime import RealtimeProvider
from journal_search.ports.storage import StorageProvider
from journal_search.ports.text_cleanup import TextCleanupProvider

_app_container: "Container | None" = None


def set_app_container(container: "Container") -> None:
    """Register the application container for workflow and API access."""
    global _app_container
    _app_container = container


def _require_container() -> "Container":
    if _app_container is None:
        raise RuntimeError("Application container not initialized")
    return _app_container


def get_ocr() -> OCRProvider:
    """Get the OCR provider."""
    return _require_container().ocr


def get_embedder() -> EmbeddingProvider:
    """Get the embedding provider."""
    return _require_container().embedder


def get_storage() -> StorageProvider:
    """Get the storage provider."""
    return _require_container().storage


def get_auth() -> AuthProvider:
    """Get the auth provider."""
    return _require_container().auth


def get_realtime() -> RealtimeProvider:
    """Get the realtime provider."""
    return _require_container().realtime


def get_text_cleanup() -> TextCleanupProvider | None:
    """Get the optional text cleanup provider."""
    container = _app_container
    return container._text_cleanup if container is not None else None


class Container:
    """Dependency container for bootstrapping the application."""

    def __init__(
        self,
        ocr: OCRProvider | None = None,
        embedder: EmbeddingProvider | None = None,
        storage: StorageProvider | None = None,
        auth: AuthProvider | None = None,
        realtime: RealtimeProvider | None = None,
        ai_sdk: LLMService | None = None,
        text_cleanup: TextCleanupProvider | None = None,
        supabase: SupabaseClient | None = None,
    ) -> None:
        self._ocr = ocr
        self._embedder = embedder
        self._storage = storage
        self._auth = auth
        self._realtime = realtime
        self._ai_sdk = ai_sdk
        self._text_cleanup = text_cleanup
        self._supabase = supabase

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
    def auth(self) -> AuthProvider:
        if self._auth is None:
            raise RuntimeError("Auth provider not configured")
        return self._auth

    @property
    def realtime(self) -> RealtimeProvider:
        if self._realtime is None:
            raise RuntimeError("Realtime provider not configured")
        return self._realtime

    @property
    def ai_sdk(self) -> LLMService:
        if self._ai_sdk is None:
            raise RuntimeError("AI SDK not configured")
        return self._ai_sdk

    @property
    def text_cleanup(self) -> TextCleanupProvider | None:
        return self._text_cleanup

    def install(self) -> None:
        """Register this container as the application singleton."""
        set_app_container(self)

    async def close(self) -> None:
        """Release adapter resources such as HTTP clients and thread pools."""
        if self._ocr is not None and hasattr(self._ocr, "close"):
            await self._ocr.close()
        if self._text_cleanup is not None and hasattr(self._text_cleanup, "close"):
            await self._text_cleanup.close()
        if self._embedder is not None and hasattr(self._embedder, "close"):
            await self._embedder.close()
        if self._supabase is not None:
            await self._supabase.close()


def create_ocr_provider(provider_name: str, **kwargs: object) -> OCRProvider:
    """Factory for creating OCR providers."""
    if provider_name == "tesseract":
        return cast(OCRProvider, TesseractOCR(**kwargs))
    if provider_name == "surya":
        return cast(OCRProvider, SuryaOCR(**kwargs))
    if provider_name == "google_vision":
        return cast(OCRProvider, GoogleVisionOCR(**kwargs))
    raise ValueError(f"Unknown OCR provider: {provider_name}")


def create_text_cleanup_provider(llm: LLMService) -> TextCleanupProvider:
    """Factory for creating text cleanup providers."""
    return TextCleanup(llm)


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
        if credentials_file:
            api_key = None
        return create_ocr_provider(
            "google_vision",
            api_key=api_key,
            credentials_file=credentials_file,
        )

    return create_ocr_provider(settings.ocr_provider.value)


def create_embedding_provider_from_settings(settings: Settings) -> EmbeddingProvider:
    """Create an embedding provider from application settings."""
    return build_embedding_provider(settings)


def create_text_cleanup_provider_from_settings(
    settings: Settings,
    ai_sdk: LLMService | None,
    *,
    enabled: bool | None = None,
) -> TextCleanupProvider | None:
    """Create a text cleanup provider when enabled and AI SDK is available."""
    if enabled is None:
        enabled = settings.llm_cleanup_enabled
    if not enabled or ai_sdk is None:
        return None

    return create_text_cleanup_provider(ai_sdk)
