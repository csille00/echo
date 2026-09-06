"""Application configuration with Pydantic Settings."""

from enum import Enum
from functools import lru_cache
import os

from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OCRProvider(str, Enum):
    TESSERACT = "tesseract"
    SURYA = "surya"
    GOOGLE_VISION = "google_vision"


class EmbeddingProvider(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: PostgresDsn = Field(
        description="PostgreSQL connection string (Supabase)"
    )

    # Supabase
    supabase_url: str = Field(description="Supabase project URL")
    supabase_key: SecretStr = Field(description="Supabase service role key")
    supabase_storage_bucket: str = Field(
        default="journal-pages",
        description="Storage bucket for journal images",
    )

    # OCR Configuration
    ocr_provider: OCRProvider = Field(
        default=OCRProvider.TESSERACT,
        description="Which OCR provider to use",
    )

    # Embedding Configuration
    embedding_provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OLLAMA,
        description="Which embedding provider to use",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Model name for embeddings",
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension",
    )

    # OpenAI (optional)
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key for embeddings",
    )

    # Google Cloud Vision (optional)
    google_vision_api_key: SecretStr | None = Field(
        default=None,
        description="Google Cloud Vision API key for OCR",
    )
    google_vision_credentials_file: str | None = Field(
        default=None,
        description="Path to Google service account JSON for Vision OCR",
    )

    @model_validator(mode="after")
    def resolve_google_credentials(self) -> "Settings":
        if self.google_vision_credentials_file is None:
            self.google_vision_credentials_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        return self

    # Ollama (optional)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )

    # LLM text cleanup (optional)
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="Which LLM provider to use for OCR text cleanup",
    )
    llm_model: str = Field(
        default="llama3.2",
        description="Model name for OCR text cleanup",
    )
    llm_cleanup_enabled: bool = Field(
        default=False,
        description="Run LLM cleanup on OCR output in the processing pipeline",
    )

    # App settings
    debug: bool = Field(default=False)
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
