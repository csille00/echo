"""Auth adapter factory."""

from typing import assert_never

from echo.adapters.auth.authentik import AuthentikAuth
from echo.adapters.auth.dev_header import DevHeaderAuth
from echo.adapters.auth.local import LocalAuth
from echo.adapters.supabase.auth import SupabaseAuth
from echo.adapters.supabase.client import SupabaseClient
from echo.config import AuthBackend, Settings
from echo.ports.auth import AuthProvider


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
