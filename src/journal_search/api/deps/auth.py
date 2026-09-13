"""Authentication dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends
from starlette.requests import Request

from journal_search.dependencies import get_auth


async def get_current_user_id(request: Request) -> UUID:
    """Resolve the authenticated user via the configured auth port."""
    return await get_auth().resolve_user_id(request)


CurrentUser = Annotated[UUID, Depends(get_current_user_id)]
