"""Realtime adapter factory."""

from echo.adapters.realtime.noop import NoopRealtime
from echo.adapters.supabase.client import SupabaseClient
from echo.adapters.supabase.realtime import SupabaseRealtime
from echo.config import RealtimeBackend, Settings
from echo.ports.realtime import RealtimeProvider


def create_realtime_provider(
    settings: Settings,
    supabase: SupabaseClient | None = None,
) -> RealtimeProvider:
    """Create the configured realtime adapter."""
    if settings.realtime_backend == RealtimeBackend.NONE:
        return NoopRealtime()

    if settings.realtime_backend == RealtimeBackend.SUPABASE:
        if supabase is None:
            raise ValueError("Supabase client required for REALTIME_BACKEND=supabase")
        return SupabaseRealtime(supabase)

    raise ValueError(f"Unknown realtime backend: {settings.realtime_backend}")
