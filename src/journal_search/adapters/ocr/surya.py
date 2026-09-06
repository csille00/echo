"""Surya OCR adapter."""

import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from io import BytesIO

from PIL import Image
from surya.recognition import RecognitionPredictor

from journal_search.core.models import OCRResult


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

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """Extract text using Surya OCR."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            image_data,
        )

    def _load_model(self) -> None:
        """Lazy load the Surya model."""
        if self._predictor is None:
            self._predictor = RecognitionPredictor()

    def _extract_sync(self, image_data: bytes) -> OCRResult:
        """Synchronous extraction - runs in thread pool."""
        self._load_model()
        assert self._predictor is not None

        image = Image.open(BytesIO(image_data))
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Run full-page OCR (most accurate for handwritten text)
        results = self._predictor([image], full_page=True)

        # Extract text from block-level HTML output
        text_blocks: list[str] = []

        for page in results:
            for block in page.blocks:
                if block.skipped or block.error or not block.html:
                    continue
                text_blocks.append(_html_to_text(block.html))

        full_text = "\n".join(text_blocks)

        return OCRResult(
            text=full_text.strip(),
            confidence=None,
            model=self.name,
            raw_response=None,
        )


def _html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", html)
    return unescape(re.sub(r"\s+", " ", text)).strip()
