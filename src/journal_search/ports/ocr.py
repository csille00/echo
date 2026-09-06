"""OCR Provider interface."""

from typing import Protocol

from journal_search.core.models import OCRResult


class OCRProvider(Protocol):
    """Interface for OCR extraction services."""

    @property
    def name(self) -> str:
        """Provider name for logging and storage."""
        ...

    def supported_formats(self) -> list[str]:
        """List of supported image formats (e.g., ['png', 'jpg', 'webp'])."""
        ...

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """
        Extract text from an image.

        Args:
            image_data: Raw image bytes
            format_hint: Optional hint about image format (e.g., 'png')

        Returns:
            OCRResult with extracted text and metadata
        """
        ...
