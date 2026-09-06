"""Ports - interfaces for external services."""

from journal_search.ports.embedder import EmbeddingProvider
from journal_search.ports.ocr import OCRProvider
from journal_search.ports.storage import StorageProvider

__all__ = ["OCRProvider", "EmbeddingProvider", "StorageProvider"]
