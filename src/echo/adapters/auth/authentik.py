"""Authentik SSO: forward-auth headers and optional OIDC Bearer tokens."""

from uuid import UUID

from fastapi import HTTPException
from starlette.requests import Request

from echo.adapters.auth.jwks import JwksValidator
from echo.config import Settings


def _parse_user_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID in auth context") from None


def _uid_from_claims(claims: dict[str, object]) -> UUID:
    for key in ("sub", "uuid", "user_id"):
        raw = claims.get(key)
        if isinstance(raw, str) and raw:
            try:
                return UUID(raw)
            except ValueError:
                continue
    raise HTTPException(status_code=401, detail="Token missing a UUID user identifier")


class AuthentikAuth:
    """Authenticate via Authentik proxy headers or OIDC JWT."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._uid_header = settings.authentik_uid_header
        self._validator: JwksValidator | None = None
        if settings.oidc_jwks_url:
            self._validator = JwksValidator(
                settings.oidc_jwks_url,
                issuer=settings.oidc_issuer or None,
                audience=settings.oidc_audience or None,
            )

    async def resolve_user_id(self, request: Request) -> UUID:
        authorization = request.headers.get("Authorization")
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.removeprefix("Bearer ").strip()
            if not self._validator:
                raise HTTPException(
                    status_code=401,
                    detail="Bearer tokens require OIDC_JWKS_URL to be configured",
                )
            try:
                claims = self._validator.decode_user_token(token)
            except Exception as exc:
                raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
            return _uid_from_claims(claims)

        if self._settings.authentik_forward_auth:
            uid = request.headers.get(self._uid_header)
            if uid:
                return _parse_user_uuid(uid.strip())

        raise HTTPException(
            status_code=401,
            detail="Authentication required (Authentik SSO or Bearer token)",
        )
