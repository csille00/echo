"""Google Cloud Vision OCR adapter."""

import asyncio
import base64
import os
import time
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from journal_search.core.models import OCRResult

_VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"
_VISION_SCOPE = "https://www.googleapis.com/auth/cloud-vision"
_TOKEN_REFRESH_BUFFER_SECONDS = 60


class GoogleVisionOCR:
    """OCR provider using Google Cloud Vision document text detection."""

    def __init__(
        self,
        api_key: str | None = None,
        credentials_file: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key and not credentials_file:
            raise ValueError(
                "Google Vision credentials required. Provide api_key or credentials_file."
            )

        if credentials_file and not api_key:
            if not os.path.isfile(credentials_file):
                raise ValueError(f"Google Vision credentials file not found: {credentials_file}")

        self._api_key = api_key
        self._credentials_file = credentials_file
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    @property
    def name(self) -> str:
        return "google-vision:document-text-detection"

    def supported_formats(self) -> list[str]:
        return ["png", "jpg", "jpeg", "webp", "tiff", "bmp", "gif"]

    async def close(self) -> None:
        """Close the underlying HTTP client if owned by this adapter."""
        if self._owns_client:
            await self._client.aclose()

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
            headers["Authorization"] = f"Bearer {await self._get_access_token()}"

        response = await self._client.post(
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
        )

    async def _get_access_token(self) -> str:
        if not self._credentials_file:
            raise ValueError("Service account credentials file path is required")

        now = time.time()
        if self._access_token and now < self._token_expiry - _TOKEN_REFRESH_BUFFER_SECONDS:
            return self._access_token

        token, expiry = await asyncio.to_thread(
            _refresh_service_account_token,
            self._credentials_file,
        )
        self._access_token = token
        self._token_expiry = expiry
        return token


def _refresh_service_account_token(credentials_file: str) -> tuple[str, float]:
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=[_VISION_SCOPE],
    )
    credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise RuntimeError("Failed to obtain Google Vision access token")

    expiry = credentials.expiry.timestamp() if credentials.expiry else time.time() + 3600
    return token, expiry


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
