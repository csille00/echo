"""Auth adapter factory."""

from journal_search.adapters.auth.dev_header import DevHeaderAuth
from journal_search.adapters.supabase.auth import SupabaseAuth
from journal_search.adapters.supabase.client import SupabaseClient
from journal_search.config import AuthBackend, Settings
from journal_search.ports.auth import AuthProvider


def create_auth_provider(
    settings: Settings,
    supabase: SupabaseClient | None = None,
) -> AuthProvider:
    """Create the configured auth adapter."""
    if settings.auth_backend == AuthBackend.DEV_HEADER:
        return DevHeaderAuth()

    if settings.auth_backend == AuthBackend.SUPABASE:
        if supabase is None:
            raise ValueError("Supabase client required for AUTH_BACKEND=supabase")
        return SupabaseAuth(supabase)

    raise ValueError(f"Unknown auth backend: {settings.auth_backend}")
