"""Realtime notification port."""

from typing import Protocol
from uuid import UUID

from journal_search.core.models import ProcessingStatus


class RealtimeProvider(Protocol):
    """Push live updates to clients (e.g. entry processing status)."""

    async def notify_entry_status(
        self,
        entry_id: UUID,
        user_id: UUID,
        status: ProcessingStatus,
    ) -> None:
        """Notify subscribers that an entry's processing status changed."""
