"""Google Cloud Vision OCR adapter."""

import base64
import os
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from journal_search.core.models import OCRResult

_VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
_VISION_SCOPE = "https://www.googleapis.com/auth/cloud-vision"


class GoogleVisionOCR:
    """OCR provider using Google Cloud Vision document text detection."""

    def __init__(
        self,
        api_key: str | None = None,
        credentials_file: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GOOGLE_VISION_API_KEY")
        self._credentials_file = (
            credentials_file
            or os.environ.get("GOOGLE_VISION_CREDENTIALS_FILE")
            or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        )

        if not self._api_key and not self._credentials_file:
            raise ValueError(
                "Google Vision credentials required. Set either "
                "GOOGLE_VISION_API_KEY or GOOGLE_APPLICATION_CREDENTIALS."
            )

        if self._credentials_file and not os.path.isfile(self._credentials_file):
            raise ValueError(
                f"Google Vision credentials file not found: {self._credentials_file}"
            )

    @property
    def name(self) -> str:
        return "google-vision:document-text-detection"

    def supported_formats(self) -> list[str]:
        return ["png", "jpg", "jpeg", "webp", "tiff", "bmp", "gif"]

    async def extract(self, image_data: bytes, format_hint: str | None = None) -> OCRResult:
        """Extract text using Google Cloud Vision API."""
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(image_data).decode("ascii")},
                    "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                }
            ]
        }

        headers: dict[str, str] = {}
        params: dict[str, str] = {}
        if self._api_key:
            params["key"] = self._api_key
        else:
            headers["Authorization"] = f"Bearer {_get_access_token(self._credentials_file)}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                _VISION_API_URL,
                params=params,
                headers=headers,
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        first_response = data.get("responses", [{}])[0]
        if "error" in first_response:
            message = first_response["error"].get("message", "Unknown Vision API error")
            raise RuntimeError(message)

        annotation = first_response.get("fullTextAnnotation", {})
        text = annotation.get("text", "")

        return OCRResult(
            text=text.strip(),
            confidence=_average_symbol_confidence(annotation),
            model=self.name,
            raw_response=None,
        )


def _get_access_token(credentials_file: str | None) -> str:
    """Get a short-lived access token from a service account JSON file."""
    if not credentials_file:
        raise ValueError("Service account credentials file path is required")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=[_VISION_SCOPE],
    )
    credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise RuntimeError("Failed to obtain Google Vision access token")
    return token


def _average_symbol_confidence(annotation: dict[str, Any]) -> float | None:
    """Compute average symbol confidence from a fullTextAnnotation."""
    confidences: list[float] = []

    for page in annotation.get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    for symbol in word.get("symbols", []):
                        if "confidence" in symbol:
                            confidences.append(float(symbol["confidence"]))

    if not confidences:
        return None

    return sum(confidences) / len(confidences)
