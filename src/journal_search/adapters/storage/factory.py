"""Storage adapter factory."""

from journal_search.adapters.storage.local import LocalFilesystemStorage
from journal_search.adapters.supabase.client import SupabaseClient
from journal_search.adapters.supabase.storage import SupabaseStorage
from journal_search.config import Settings, StorageBackend
from journal_search.ports.storage import StorageProvider


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
