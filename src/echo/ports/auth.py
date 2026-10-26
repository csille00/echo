"""Authentication port."""

from typing import Protocol
from uuid import UUID

from starlette.requests import Request


class AuthProvider(Protocol):
    """Resolve the authenticated user for a request."""

    async def resolve_user_id(self, request: Request) -> UUID:
        """Return the user ID for the request, or raise if unauthenticated."""
