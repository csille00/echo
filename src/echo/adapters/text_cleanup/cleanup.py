"""OCR text cleanup using the app-level AI SDK."""

from echo.adapters.text_cleanup.preprocess import split_by_date
from echo.adapters.text_cleanup.prompt import SYSTEM_PROMPT
from echo.core.models import TextCleanupResult
from echo.ports.llm import LLMService


class TextCleanup:
    """Clean OCR text via an injected LLM service."""

    def __init__(self, llm: LLMService) -> None:
        self._llm = llm

    @property
    def name(self) -> str:
        return self._llm.name

    async def cleanup(
        self,
        raw_text: str,
        source_model: str | None = None,
    ) -> TextCleanupResult:
        sections = split_by_date(raw_text)
        if not sections:
            raise RuntimeError("No OCR text to clean")

        cleaned_parts: list[str] = []
        for section in sections:
            cleaned_parts.append(
                await self._llm.generate(
                    system=SYSTEM_PROMPT,
                    user=section,
                    temperature=0.0,
                    max_tokens=max(len(section) * 2, 4_096),
                )
            )

        cleaned = "\n\n".join(part.strip() for part in cleaned_parts if part.strip())
        if not cleaned:
            raise RuntimeError("LLM returned empty cleanup response")

        return TextCleanupResult(
            text=cleaned,
            model=self.name,
            source_model=source_model,
        )
