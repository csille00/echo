"""Application configuration.

Self-hosted by default: PostgreSQL, local filesystem storage, and self-hosted DBOS.
Google Cloud provides OCR and optional embeddings when local models are unavailable.
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
    GOOGLE = "google"


class LLMProvider(StrEnum):
    OLLAMA = "ollama"


class StorageBackend(StrEnum):
    LOCAL = "local"
    SUPABASE = "supabase"


class AuthBackend(StrEnum):
    LOCAL = "local"
    DEV_HEADER = "dev_header"
    SUPABASE = "supabase"
    AUTHENTIK = "authentik"


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
        default=AuthBackend.LOCAL,
        description=(
            "Authentication backend: local, dev_header, supabase, or authentik proxy-header mode"
        ),
    )
    session_ttl_days: int = Field(
        default=30,
        ge=1,
        description="Lifetime of a local-account session cookie",
    )
    session_cookie_secure: bool = Field(
        default=False,
        description="Set the session cookie Secure flag (enable behind HTTPS)",
    )

    # Reverse-proxy header auth (AUTH_BACKEND=authentik). Optional.
    # The header default matches Authentik forward-auth; point it at whatever
    # your proxy sends. This is separate from the OIDC login below.
    authentik_forward_auth: bool = Field(
        default=True,
        description="Trust a user-id header injected by the reverse proxy",
    )
    authentik_uid_header: str = Field(
        default="X-Authentik-Uid",
        description="Proxy header that carries the user UUID",
    )

    # Generic OpenID Connect login. Set issuer, client id, and client secret
    # to add a "Sign in with SSO" button for any OIDC provider.
    oidc_issuer: str = Field(
        default="",
        description="OIDC issuer URL. Discovery is fetched from this URL.",
    )
    oidc_client_id: str = Field(default="", description="OIDC client id")
    oidc_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="OIDC client secret",
    )
    oidc_scopes: str = Field(default="openid profile email")
    oidc_display_name: str = Field(
        default="SSO",
        description="Label for the SSO button",
    )
    oidc_auto_register: bool = Field(
        default=True,
        description="Create an account on first SSO sign-in. The first account is the admin.",
    )
    public_url: str = Field(
        default="",
        description="Public origin, used to build the OIDC redirect URL behind a proxy",
    )
    oidc_jwks_url: str = Field(
        default="",
        description="Optional JWKS URL override. Discovery supplies this when empty.",
    )
    oidc_audience: str = Field(
        default="",
        description="Optional expected JWT aud. Defaults to the OIDC client id.",
    )

    @property
    def oidc_enabled(self) -> bool:
        """True when a generic OIDC login button should be offered."""
        return bool(
            self.oidc_issuer.strip()
            and self.oidc_client_id.strip()
            and self.oidc_client_secret.get_secret_value().strip()
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
        default=OCRProvider.TESSERACT,
        description="OCR provider (tesseract/surya are on-prem; google_vision uses Google Cloud)",
    )

    # Embeddings (Ollama on-prem or Google Cloud API)
    embedding_provider: EmbeddingProvider = Field(
        default=EmbeddingProvider.OLLAMA,
        description="Embedding provider: ollama or google",
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model (nomic-embed-text for Ollama, or a Google model)",
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension (768 for text-embedding-004 / nomic-embed-text)",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL when EMBEDDING_PROVIDER=ollama",
    )
    google_embedding_api_key: SecretStr | None = Field(
        default=None,
        description="Google API key for embeddings; falls back to GOOGLE_VISION_API_KEY",
    )
    google_embedding_credentials_file: str | None = Field(
        default=None,
        description="Service account JSON for embeddings; falls back to Vision credentials",
    )

    # Google Cloud Vision (external)
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
        if self.google_embedding_credentials_file is None:
            self.google_embedding_credentials_file = self.google_vision_credentials_file
        if self.google_embedding_api_key is None:
            self.google_embedding_api_key = self.google_vision_api_key
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
    api_host: str = Field(
        default="127.0.0.1",
        description="Address the API binds to. Use 0.0.0.0 inside a container.",
    )
    listen_port: int = Field(default=8000, ge=1, le=65535)
    web_root: str = Field(
        default="",
        description="Directory of the built web UI. Empty disables static serving.",
    )
    debug: bool = Field(default=False)
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
