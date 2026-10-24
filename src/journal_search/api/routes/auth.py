"""Auth introspection (for SPAs behind Authentik forward-auth)."""

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from journal_search.api.deps.auth import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


class WhoamiResponse(BaseModel):
    user_id: UUID


@router.get("/whoami", response_model=WhoamiResponse)
async def whoami(user_id: CurrentUser) -> WhoamiResponse:
    """Return the resolved user id for the current request."""
    return WhoamiResponse(user_id=user_id)
