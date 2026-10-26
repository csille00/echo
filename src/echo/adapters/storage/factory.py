"""Storage adapter factory."""

from echo.adapters.storage.local import LocalFilesystemStorage
from echo.adapters.supabase.client import SupabaseClient
from echo.adapters.supabase.storage import SupabaseStorage
from echo.config import Settings, StorageBackend
from echo.ports.storage import StorageProvider


async def create_storage_provider(
    settings: Settings,
    supabase: SupabaseClient | None = None,
) -> StorageProvider:
    """Create the configured object storage adapter."""
    if settings.storage_backend == StorageBackend.LOCAL:
        return LocalFilesystemStorage(settings.local_storage_path)

    if settings.storage_backend == StorageBackend.SUPABASE:
        if supabase is None:
            raise ValueError("Supabase client required for STORAGE_BACKEND=supabase")
        return SupabaseStorage(supabase)

    raise ValueError(f"Unknown storage backend: {settings.storage_backend}")
