"""Supabase Auth adapter."""

from uuid import UUID

from fastapi import HTTPException
from starlette.requests import Request

from echo.adapters.supabase.client import SupabaseClient


class SupabaseAuth:
    """Authenticate requests using Supabase JWTs."""

    def __init__(self, supabase: SupabaseClient) -> None:
        self._client = supabase.client

    async def resolve_user_id(self, request: Request) -> UUID:
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer token required")

        token = authorization.removeprefix("Bearer ").strip()
        try:
            response = await self._client.auth.get_user(token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

        if response.user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        try:
            return UUID(response.user.id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid user ID in token") from None
