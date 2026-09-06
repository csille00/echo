"""OCR adapter implementations."""

from journal_search.adapters.ocr.google_vision import GoogleVisionOCR
from journal_search.adapters.ocr.surya import SuryaOCR
from journal_search.adapters.ocr.tesseract import TesseractOCR

__all__ = ["GoogleVisionOCR", "SuryaOCR", "TesseractOCR"]
