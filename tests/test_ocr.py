"""Tests for OCR adapters."""

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image as PILImage

from journal_search.adapters.ocr.tesseract import TesseractOCR


class TestTesseractOCR:
    def test_name(self) -> None:
        ocr = TesseractOCR(lang="eng")
        assert ocr.name == "tesseract:eng"

    def test_supported_formats(self) -> None:
        ocr = TesseractOCR()
        formats = ocr.supported_formats()
        assert "png" in formats
        assert "jpg" in formats

    @pytest.mark.asyncio
    async def test_extract_returns_ocr_result(self) -> None:
        """Test that extract returns properly structured result."""
        ocr = TesseractOCR()

        img = PILImage.new("RGB", (100, 100), color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_data = buf.getvalue()

        with patch("journal_search.adapters.ocr.tesseract.pytesseract") as mock_pytesseract:
            mock_pytesseract.image_to_string.return_value = "Hello World"
            mock_pytesseract.image_to_data.return_value = {
                "conf": [95, 90, -1, 85],
            }
            mock_pytesseract.Output.DICT = "dict"

            result = await ocr.extract(image_data)

            assert result.text == "Hello World"
            assert result.model == "tesseract:eng"
            assert result.confidence == pytest.approx(0.9, rel=0.01)
