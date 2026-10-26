"""LLM service interface."""

from typing import Protocol


class LLMService(Protocol):
    """Interface for app-level LLM text generation."""

    @property
    def name(self) -> str:
        """Provider and model identifier for logging."""
        ...

    async def generate(
        self,
        *,
        system: str | None = None,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from optional system and user prompts."""
        ...
