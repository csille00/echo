"""Supabase client lifecycle — the only module that imports the Supabase SDK."""

from dataclasses import dataclass

from supabase import AsyncClient, acreate_client

from journal_search.config import AuthBackend, RealtimeBackend, Settings, StorageBackend


@dataclass
class SupabaseClient:
    """Shared Supabase client and settings for adapters in this package."""

    client: AsyncClient
    storage_bucket: str

    async def close(self) -> None:
        if hasattr(self.client, "aclose"):
            await self.client.aclose()


def supabase_required(settings: Settings) -> bool:
    """Return whether any configured backend needs a Supabase client."""
    return (
        settings.storage_backend == StorageBackend.SUPABASE
        or settings.auth_backend == AuthBackend.SUPABASE
        or settings.realtime_backend == RealtimeBackend.SUPABASE
    )


async def create_supabase_client(settings: Settings) -> SupabaseClient:
    """Create a Supabase client from application settings."""
    if not settings.supabase_url:
        raise ValueError("SUPABASE_URL is required when a Supabase backend is enabled")
    if settings.supabase_service_key.get_secret_value() == "":
        raise ValueError("SUPABASE_SERVICE_KEY is required when a Supabase backend is enabled")

    client = await acreate_client(
        settings.supabase_url,
        settings.supabase_service_key.get_secret_value(),
    )
    return SupabaseClient(client=client, storage_bucket=settings.supabase_storage_bucket)
