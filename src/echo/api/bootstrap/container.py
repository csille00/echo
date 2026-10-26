"""Application container bootstrap."""

from echo.adapters.ai_sdk.factory import create_ai_sdk_from_settings
from echo.adapters.auth.factory import create_auth_provider
from echo.adapters.realtime.factory import create_realtime_provider
from echo.adapters.storage.factory import create_storage_provider
from echo.adapters.supabase.client import (
    SupabaseClient,
    create_supabase_client,
    supabase_required,
)
from echo.config import Settings
from echo.dependencies import (
    Container,
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
