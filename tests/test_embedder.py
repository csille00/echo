"""Tests for embedding adapters."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from journal_search.adapters.embedders.ollama import OllamaEmbedder


class TestOllamaEmbedder:
    def test_name(self) -> None:
        embedder = OllamaEmbedder(model="nomic-embed-text")
        assert embedder.name == "ollama:nomic-embed-text"

    def test_dimension(self) -> None:
        embedder = OllamaEmbedder(dimension=768)
        assert embedder.dimension == 768

    @pytest.mark.asyncio
    async def test_embed_returns_embedding_result(self) -> None:
        """Test that embed returns properly structured result."""
        embedder = OllamaEmbedder()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3] * 256,  # 768 dims
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            result = await embedder.embed("Hello world")

            assert len(result.embedding) == 768
            assert result.model == "ollama:nomic-embed-text"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_batch(self) -> None:
        """Test batch embedding."""
        embedder = OllamaEmbedder()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "embedding": [0.1] * 768,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(embedder._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            results = await embedder.embed_batch(["text1", "text2", "text3"])

            assert len(results) == 3
            assert mock_post.call_count == 3
