"""Google Generative Language embedding adapter."""

import asyncio
import os
import time

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from journal_search.core.models import EmbeddingResult

_EMBED_SCOPE = "https://www.googleapis.com/auth/generative-language"
_TOKEN_REFRESH_BUFFER_SECONDS = 60


class GoogleEmbedder:
    """Embedding provider using Google's text-embedding models."""

    def __init__(
        self,
        model: str = "text-embedding-004",
        dimension: int = 768,
        api_key: str | None = None,
        credentials_file: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key and not credentials_file:
            raise ValueError(
                "Google embedding credentials required. Provide api_key or credentials_file."
            )

        if credentials_file and not api_key and not os.path.isfile(credentials_file):
            raise ValueError(f"Google credentials file not found: {credentials_file}")

        self._model = model
        self._dimension = dimension
        self._api_key = api_key
        self._credentials_file = credentials_file
        self._client = client or httpx.AsyncClient(timeout=60.0)
        self._owns_client = client is None
        self._access_token: str | None = None
        self._token_expiry: float = 0.0

    @property
    def name(self) -> str:
        return f"google:{self._model}"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def embed(self, text: str) -> EmbeddingResult:
        values = await self._embed_text(text)
        return EmbeddingResult(
            embedding=values,
            model=self.name,
            token_count=None,
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return list(await asyncio.gather(*(self.embed(text) for text in texts)))

    async def _embed_text(self, text: str) -> list[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:embedContent"
        params: dict[str, str] = {}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            params["key"] = self._api_key
        else:
            headers["Authorization"] = f"Bearer {await self._get_access_token()}"

        response = await self._client.post(
            url,
            params=params,
            headers=headers,
            json={
                "model": f"models/{self._model}",
                "content": {"parts": [{"text": text}]},
            },
        )
        response.raise_for_status()
        data = response.json()
        values = data.get("embedding", {}).get("values")
        if not isinstance(values, list):
            raise ValueError("Google embedding API returned an unexpected response")

        return values

    async def _get_access_token(self) -> str:
        if (
            self._access_token is not None
            and time.time() < self._token_expiry - _TOKEN_REFRESH_BUFFER_SECONDS
        ):
            return self._access_token

        if not self._credentials_file:
            raise ValueError("Service account credentials required for bearer auth")

        credentials = service_account.Credentials.from_service_account_file(
            self._credentials_file,
            scopes=[_EMBED_SCOPE],
        )
        credentials.refresh(Request())
        if credentials.token is None:
            raise ValueError("Failed to obtain Google access token")

        self._access_token = credentials.token
        expiry = credentials.expiry
        self._token_expiry = expiry.timestamp() if expiry is not None else time.time() + 3600
        return self._access_token
