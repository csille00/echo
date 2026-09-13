"""Realtime adapter factory."""

from journal_search.adapters.realtime.noop import NoopRealtime
from journal_search.adapters.supabase.client import SupabaseClient
from journal_search.adapters.supabase.realtime import SupabaseRealtime
from journal_search.config import RealtimeBackend, Settings
from journal_search.ports.realtime import RealtimeProvider


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
