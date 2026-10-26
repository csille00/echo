"""Auth adapter factory."""

from typing import assert_never

from journal_search.adapters.auth.authentik import AuthentikAuth
from journal_search.adapters.auth.dev_header import DevHeaderAuth
from journal_search.adapters.auth.local import LocalAuth
from journal_search.adapters.supabase.auth import SupabaseAuth
from journal_search.adapters.supabase.client import SupabaseClient
from journal_search.config import AuthBackend, Settings
from journal_search.ports.auth import AuthProvider


def create_auth_provider(
    settings: Settings,
    supabase: SupabaseClient | None = None,
) -> AuthProvider:
    """Create the configured auth adapter."""
    match settings.auth_backend:
        case AuthBackend.LOCAL:
            return LocalAuth()
        case AuthBackend.DEV_HEADER:
            return DevHeaderAuth()
        case AuthBackend.SUPABASE:
            if supabase is None:
                raise ValueError("Supabase client required for AUTH_BACKEND=supabase")
            return SupabaseAuth(supabase)
        case AuthBackend.AUTHENTIK:
            return AuthentikAuth(settings)
        case _ as unreachable:
            assert_never(unreachable)
