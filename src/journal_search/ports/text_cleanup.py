"""Text cleanup provider interface."""

from typing import Protocol

from journal_search.core.models import TextCleanupResult


class TextCleanupProvider(Protocol):
    """Interface for LLM-based cleanup of OCR output."""

    @property
    def name(self) -> str:
        """Provider name for logging and storage."""
        ...

    async def cleanup(
        self,
        raw_text: str,
        source_model: str | None = None,
    ) -> TextCleanupResult:
        """
        Clean and format raw OCR text without changing meaning.

        Args:
            raw_text: Unprocessed OCR output
            source_model: Optional OCR model name for provenance

        Returns:
            TextCleanupResult with polished text
        """
        ...
