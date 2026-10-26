"""Ports - interfaces for external services."""

from echo.ports.auth import AuthProvider
from echo.ports.embedder import EmbeddingProvider
from echo.ports.ocr import OCRProvider
from echo.ports.realtime import RealtimeProvider
from echo.ports.storage import StorageProvider

__all__ = [
    "AuthProvider",
    "EmbeddingProvider",
    "OCRProvider",
    "RealtimeProvider",
    "StorageProvider",
]
