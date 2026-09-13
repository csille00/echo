"""App-level Vercel AI SDK client (Ollama via OpenAI-compatible API)."""

import ai

# Ollama's OpenAI-compatible endpoint requires an api_key field but ignores the value.
_OLLAMA_PLACEHOLDER_API_KEY = "ollama"


class AISDK:
    """Configured Vercel AI SDK instance for self-hosted Ollama."""

    def __init__(
        self,
        model: str,
        provider: str = "ollama",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        if provider != "ollama":
            raise ValueError(f"Only ollama is supported for self-hosted LLM cleanup, got: {provider}")
        if not base_url:
            raise ValueError("Ollama base URL required")

        self._provider_name = provider
        self._model_name = model
        ollama_base = base_url.rstrip("/")
        ai_provider = ai.get_provider(
            "openai",
            base_url=f"{ollama_base}/v1",
            api_key=api_key or _OLLAMA_PLACEHOLDER_API_KEY,
        )
        self._model = ai.Model(id=model, provider=ai_provider)

    @property
    def name(self) -> str:
        return f"{self._provider_name}:{self._model_name}"

    @property
    def model(self) -> ai.Model:
        return self._model

    async def generate(
        self,
        *,
        system: str | None = None,
        user: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str:
        """Generate text from system and user prompts."""
        messages = []
        if system is not None:
            messages.append(ai.system_message(system))
        messages.append(ai.user_message(user))

        output_tokens = max_tokens or max(len(user) * 2, 4_096)
        output_tokens = min(output_tokens, 16_384)
        params = ai.InferenceRequestParams(
            output=ai.OutputParams(max_tokens=output_tokens),
        ).with_temperature(temperature)
        response = await ai.experimental_generate(self._model, messages, params=params)
        text = response.text.strip()
        if not text:
            raise RuntimeError("LLM returned empty response")
        return text
