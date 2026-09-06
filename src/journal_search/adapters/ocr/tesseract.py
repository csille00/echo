"""Tesseract OCR adapter."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytesseract

from journal_search.adapters.ocr.image_utils import open_image
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

    async def close(self) -> None:
        """Shut down the thread pool used for OCR."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """Extract text using Tesseract OCR."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_sync,
            image_data,
            format_hint,
        )

    def _extract_sync(self, image_data: bytes, format_hint: str | None) -> OCRResult:
        """Synchronous extraction - runs in thread pool."""
        image = open_image(image_data, format_hint)

        data = pytesseract.image_to_data(image, lang=self._lang, output_type=pytesseract.Output.DICT)
        text = _text_from_tesseract_data(data)

        confidences = [c for c in data["conf"] if c != -1]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        return OCRResult(
            text=text.strip(),
            confidence=avg_confidence / 100 if avg_confidence else None,
            model=self.name,
        )


def _text_from_tesseract_data(data: dict[str, list]) -> str:
    """Reconstruct line-oriented text from a single image_to_data pass."""
    lines: list[str] = []
    current_words: list[str] = []
    current_line_num = -1

    for i, word in enumerate(data["text"]):
        if data["conf"][i] == -1 or not word.strip():
            continue

        line_num = data["line_num"][i]
        if line_num != current_line_num:
            if current_words:
                lines.append(" ".join(current_words))
            current_words = [word]
            current_line_num = line_num
        else:
            current_words.append(word)

    if current_words:
        lines.append(" ".join(current_words))

    return "\n".join(lines)
