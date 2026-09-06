"""Text cleanup via the Vercel AI SDK for Python."""

import ai

from journal_search.adapters.text_cleanup.prompt import SYSTEM_PROMPT
from journal_search.core.models import TextCleanupResult

# Ollama's OpenAI-compatible endpoint requires an api_key field but ignores the value.
_OLLAMA_PLACEHOLDER_API_KEY = "ollama"


class AISDKTextCleanup:
    """Clean OCR text using the Vercel AI SDK."""

    def __init__(
        self,
        model: str,
        provider: str = "ollama",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._provider_name = provider
        self._model_name = model

        if provider == "ollama":
            if not base_url:
                raise ValueError("Ollama base URL required")
            ollama_base = base_url.rstrip("/")
            ai_provider = ai.get_provider(
                "openai",
                base_url=f"{ollama_base}/v1",
                api_key=api_key or _OLLAMA_PLACEHOLDER_API_KEY,
            )
        elif provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key required")
            ai_provider = ai.get_provider("openai", api_key=api_key)
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
            ai.system_message(SYSTEM_PROMPT),
            ai.user_message(raw_text),
        ]
        params = ai.InferenceRequestParams().with_temperature(0.2)

        response = await ai.experimental_generate(self._model, messages, params=params)
        cleaned = response.text.strip()
        if not cleaned:
            raise RuntimeError("LLM returned empty cleanup response")

        return TextCleanupResult(
            text=cleaned,
            model=self.name,
            source_model=source_model,
        )
