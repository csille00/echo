"""Supabase Realtime adapter."""

from uuid import UUID

from echo.adapters.supabase.client import SupabaseClient
from echo.core.models import ProcessingStatus


class SupabaseRealtime:
    """
    Supabase Realtime for entry status updates.

    Supabase publishes ``postgres_changes`` when the ``entries`` row is updated,
    so clients subscribe directly to the table — no server-side push is needed here.
    This adapter exists so REALTIME_BACKEND can be swapped independently of storage/auth.
    """

    def __init__(self, supabase: SupabaseClient) -> None:
        self._supabase = supabase

    async def notify_entry_status(
        self,
        entry_id: UUID,
        user_id: UUID,
        status: ProcessingStatus,
    ) -> None:
        return None
