"""Tesseract OCR adapter."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import pytesseract
from PIL import Image

from journal_search.core.models import OCRResult


class TesseractOCR:
    """OCR provider using Tesseract."""

    def __init__(self, lang: str = "eng") -> None:
        self._lang = lang
        self._executor = ThreadPoolExecutor(max_workers=2)

    @property
    def name(self) -> str:
        return f"tesseract:{self._lang}"

    def supported_formats(self) -> list[str]:
        return ["png", "jpg", "jpeg", "webp", "tiff", "bmp"]

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """Extract text using Tesseract OCR."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            image_data,
        )

    def _extract_sync(self, image_data: bytes) -> OCRResult:
        """Synchronous extraction - runs in thread pool."""
        image = Image.open(BytesIO(image_data))

        # Get detailed data for confidence
        data = pytesseract.image_to_data(image, lang=self._lang, output_type=pytesseract.Output.DICT)

        # Calculate average confidence (excluding -1 values which indicate no text)
        confidences = [c for c in data["conf"] if c != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        # Extract plain text
        text = pytesseract.image_to_string(image, lang=self._lang)

        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100 if avg_confidence else None,
            model=self.name,
            raw_response=None,  # Don't store full data dict, it's large
        )
