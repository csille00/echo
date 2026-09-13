"""Embedding adapter implementations."""

from journal_search.adapters.embedders.google import GoogleEmbedder
from journal_search.adapters.embedders.ollama import OllamaEmbedder

__all__ = ["GoogleEmbedder", "OllamaEmbedder"]
