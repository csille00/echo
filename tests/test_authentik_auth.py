"""Tests for Authentik auth adapter."""

from uuid import uuid4

import pytest
from starlette.requests import Request

from journal_search.adapters.auth.authentik import AuthentikAuth
from journal_search.config import Settings


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_forward_auth_uid_header() -> None:
    user_id = uuid4()
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://u:p@localhost/db",
        auth_backend="authentik",
        authentik_forward_auth=True,
    )
    auth = AuthentikAuth(settings)
    req = _request([(b"x-authentik-uid", str(user_id).encode())])
    assert await auth.resolve_user_id(req) == user_id


@pytest.mark.asyncio
async def test_missing_auth_returns_401() -> None:
    from fastapi import HTTPException

    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+asyncpg://u:p@localhost/db",
        auth_backend="authentik",
    )
    auth = AuthentikAuth(settings)
    with pytest.raises(HTTPException) as exc:
        await auth.resolve_user_id(_request([]))
    assert exc.value.status_code == 401
