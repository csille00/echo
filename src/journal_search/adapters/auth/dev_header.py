"""Development auth via X-User-ID header."""

from uuid import UUID

from fastapi import HTTPException
from starlette.requests import Request


class DevHeaderAuth:
    """Authenticate using the X-User-ID header (local development only)."""

    async def resolve_user_id(self, request: Request) -> UUID:
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Set X-User-ID header for development.",
            )
        try:
            return UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format") from None
