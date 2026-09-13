"""Application container bootstrap."""

from journal_search.adapters.auth.factory import create_auth_provider
from journal_search.adapters.realtime.factory import create_realtime_provider
from journal_search.adapters.storage.factory import create_storage_provider
from journal_search.adapters.supabase.client import SupabaseClient, create_supabase_client, supabase_required
from journal_search.config import Settings
from journal_search.dependencies import (
    Container,
    create_ai_sdk_from_settings,
    create_embedding_provider_from_settings,
    create_ocr_provider_from_settings,
    create_text_cleanup_provider_from_settings,
)


async def build_container(settings: Settings) -> Container:
    """Wire adapters from settings into a container."""
    supabase: SupabaseClient | None = None
    if supabase_required(settings):
        supabase = await create_supabase_client(settings)

    ai_sdk = create_ai_sdk_from_settings(settings)
    return Container(
        ocr=create_ocr_provider_from_settings(settings),
        embedder=create_embedding_provider_from_settings(settings),
        storage=await create_storage_provider(settings, supabase=supabase),
        auth=create_auth_provider(settings, supabase=supabase),
        realtime=create_realtime_provider(settings, supabase=supabase),
        ai_sdk=ai_sdk,
        text_cleanup=create_text_cleanup_provider_from_settings(settings, ai_sdk),
        supabase=supabase,
    )
