"""Embedding Provider interface."""

from typing import Protocol

from echo.core.models import EmbeddingResult


class EmbeddingProvider(Protocol):
    """Interface for text embedding services."""

    @property
    def name(self) -> str:
        """Provider name for logging and storage."""
        ...

    @property
    def dimension(self) -> int:
        """Embedding vector dimension."""
        ...

    async def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector and metadata
        """
        ...

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult in same order as input
        """
        ...
