"""Text cleanup via the Vercel AI SDK for Python."""

import os

import ai

from journal_search.adapters.text_cleanup.prompt import SYSTEM_PROMPT
from journal_search.core.models import TextCleanupResult


class AISDKTextCleanup:
    """Clean OCR text using the Vercel AI SDK."""

    def __init__(
        self,
        model: str,
        provider: str = "ollama",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._ai = ai
        self._provider_name = provider
        self._model_name = model

        if provider == "ollama":
            ollama_base = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
            ai_provider = ai.get_provider(
                "openai",
                base_url=f"{ollama_base}/v1",
                api_key=api_key or "ollama",
            )
        elif provider == "openai":
            resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not resolved_key:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
            ai_provider = ai.get_provider("openai", api_key=resolved_key)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

        self._model = ai.Model(id=model, provider=ai_provider)

    @property
    def name(self) -> str:
        return f"{self._provider_name}:{self._model_name}"

    async def cleanup(
        self,
        raw_text: str,
        source_model: str | None = None,
    ) -> TextCleanupResult:
        messages = [
            self._ai.system_message(SYSTEM_PROMPT),
            self._ai.user_message(raw_text),
        ]
        params = self._ai.InferenceRequestParams().with_temperature(0.2)

        async with self._ai.stream(self._model, messages, params=params) as stream:
            async for _event in stream:
                pass

        cleaned = stream.text.strip()
        if not cleaned:
            raise RuntimeError("LLM returned empty cleanup response")

        return TextCleanupResult(
            text=cleaned,
            model=self.name,
            source_model=source_model,
        )
