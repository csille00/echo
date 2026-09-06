"""Ollama embedding adapter."""

import httpx

from journal_search.core.models import EmbeddingResult


class OllamaEmbedder:
    """Embedding provider using Ollama."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimension: int = 768,
    ) -> None:
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._dimension = dimension
        self._client = httpx.AsyncClient(timeout=60.0)

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text."""
        response = await self._client.post(
            f"{self._base_url}/api/embeddings",
            json={
                "model": self._model,
                "prompt": text,
            },
        )
        response.raise_for_status()
        data = response.json()

        return EmbeddingResult(
            embedding=data["embedding"],
            model=self.name,
            token_count=None,  # Ollama doesn't return token count
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for multiple texts."""
        # Ollama doesn't have native batch support, so we do sequential calls
        # Could be parallelized with asyncio.gather if needed
        results: list[EmbeddingResult] = []
        for text in texts:
            result = await self.embed(text)
            results.append(result)
        return results

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
