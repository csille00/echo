"""Application configuration.

Self-hosted by default: PostgreSQL, local filesystem storage, Ollama embeddings/LLM,
and self-hosted DBOS. Google Cloud Vision is the only external cloud service (OCR).
"""

import os
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OCRProvider(StrEnum):
    TESSERACT = "tesseract"
    SURYA = "surya"
    GOOGLE_VISION = "google_vision"


class EmbeddingProvider(StrEnum):
    OLLAMA = "ollama"


class LLMProvider(StrEnum):
    OLLAMA = "ollama"


class StorageBackend(StrEnum):
    LOCAL = "local"
    SUPABASE = "supabase"


class AuthBackend(StrEnum):
    DEV_HEADER = "dev_header"
    SUPABASE = "supabase"


class RealtimeBackend(StrEnum):
    NONE = "none"
    SUPABASE = "supabase"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (self-hosted PostgreSQL)
    database_url: PostgresDsn = Field(description="PostgreSQL connection string")

    @property
    def dbos_database_url(self) -> str:
        """Sync PostgreSQL URL for DBOS (strips the asyncpg driver)."""
        return str(self.database_url).replace("postgresql+asyncpg://", "postgresql://")

    # Object storage (swap independently via STORAGE_BACKEND)
    storage_backend: StorageBackend = Field(
        default=StorageBackend.LOCAL,
        description="Object storage backend: local or supabase",
    )
    local_storage_path: str = Field(
        default="data/uploads",
        description="Directory for uploaded journal images when STORAGE_BACKEND=local",
    )

    # Auth (swap independently via AUTH_BACKEND)
    auth_backend: AuthBackend = Field(
        default=AuthBackend.DEV_HEADER,
        description="Authentication backend: dev_header or supabase",
    )

    # Realtime (swap independently via REALTIME_BACKEND)
    realtime_backend: RealtimeBackend = Field(
        default=RealtimeBackend.NONE,
        description="Realtime backend: none or supabase",
    )

    # Supabase (only read by adapters/supabase/*)
    supabase_url: str = Field(default="", description="Supabase API URL")
    supabase_service_key: SecretStr = Field(
        default=SecretStr(""),
        description="Supabase service role key",
    )
    supabase_storage_bucket: str = Field(
        default="journal-pages",
        description="Supabase Storage bucket for journal images",
    )

    # OCR — google_vision is the only external cloud service
    ocr_provider: OCRProvider = Field(
        default=OCRProvider.GOOGLE_VISION,
        description="OCR provider (google_vision uses Google Cloud; tesseract/surya are on-prem)",
    )

    # Embeddings (self-hosted Ollama)
    embedding_provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OLLAMA,
        description="Embedding provider",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Ollama model name for embeddings",
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension (768 for nomic-embed-text)",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )

    # Google Cloud Vision (external — only cloud dependency)
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

    # LLM text cleanup (self-hosted Ollama)
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM provider for OCR text cleanup",
    )
    llm_model: str = Field(
        default="llama3.2",
        description="Ollama model for OCR text cleanup",
    )
    llm_cleanup_enabled: bool = Field(
        default=False,
        description="Run LLM cleanup on OCR output in the processing pipeline",
    )

    # Self-hosted DBOS Conductor (optional — omit to run without the ops UI)
    dbos_conductor_url: str | None = Field(
        default=None,
        description="WebSocket URL for self-hosted DBOS Conductor (e.g. ws://localhost:8090/)",
    )
    dbos_conductor_key: SecretStr | None = Field(
        default=None,
        description="API key for self-hosted DBOS Conductor",
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
