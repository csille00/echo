"""Surya OCR adapter."""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape

from surya.recognition import RecognitionPredictor

from echo.adapters.ocr.image_utils import open_image
from echo.core.models import OCRResult


class SuryaOCR:
    """OCR provider using Surya (optimized for documents and handwriting)."""

    def __init__(self, langs: list[str] | None = None) -> None:
        self._langs = langs or ["en"]
        self._executor = ThreadPoolExecutor(max_workers=1)  # Surya is GPU-heavy
        self._predictor: RecognitionPredictor | None = None

    @property
    def name(self) -> str:
        return f"surya:{','.join(self._langs)}"

    def supported_formats(self) -> list[str]:
        return ["png", "jpg", "jpeg", "webp", "tiff", "bmp"]

    async def close(self) -> None:
        """Shut down the thread pool used for OCR."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """Extract text using Surya OCR."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            image_data,
            format_hint,
        )

    def _load_model(self) -> RecognitionPredictor:
        """Lazy load the Surya model."""
        if self._predictor is None:
            self._predictor = RecognitionPredictor()
        return self._predictor

    def _extract_sync(self, image_data: bytes, format_hint: str | None) -> OCRResult:
        """Synchronous extraction - runs in thread pool."""
        predictor = self._load_model()
        image = open_image(image_data, format_hint)

        results = predictor([image], full_page=True)

        text_blocks: list[str] = []
        for page in results:
            for block in page.blocks:
                if block.skipped or block.error or not block.html:
                    continue
                text_blocks.append(_html_to_text(block.html))

        return OCRResult(
            text="\n".join(text_blocks).strip(),
            confidence=None,  # Surya does not expose per-block confidence scores
            model=self.name,
        )


def _html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    return unescape(re.sub(r"\s+", " ", text)).strip()
