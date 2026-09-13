"""No-op realtime adapter."""

from uuid import UUID

from journal_search.core.models import ProcessingStatus


class NoopRealtime:
    """Discard realtime notifications."""

    async def notify_entry_status(
        self,
        entry_id: UUID,
        user_id: UUID,
        status: ProcessingStatus,
    ) -> None:
        return None
