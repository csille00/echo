"""Local accounts: session cookie issued by this app."""

from uuid import UUID

from fastapi import HTTPException
from starlette.requests import Request

from echo.adapters.auth.cookies import COOKIE_NAME
from echo.adapters.db.users import user_id_for_token
from echo.db.session import get_session


class LocalAuth:
    """Authenticate using the journal_session cookie."""

    async def resolve_user_id(self, request: Request) -> UUID:
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        async with get_session() as session:
            user_id = await user_id_for_token(session, token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return user_id
