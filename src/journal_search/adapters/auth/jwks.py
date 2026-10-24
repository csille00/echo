"""JWKS fetch and cache for OIDC access tokens."""

import time
from typing import Any

import jwt
from jwt import PyJWKClient


class JwksValidator:
    """Validate JWTs against a JWKS endpoint (e.g. Authentik OAuth provider)."""

    def __init__(
        self,
        jwks_url: str,
        *,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._jwks_url = jwks_url
        self._issuer = issuer or None
        self._audience = audience or None
        self._client: PyJWKClient | None = None
        self._client_created_at = 0.0

    def _get_client(self) -> PyJWKClient:
        # Refresh client periodically so key rotation is picked up.
        if self._client is None or time.monotonic() - self._client_created_at > 3600:
            self._client = PyJWKClient(self._jwks_url, cache_keys=True)
            self._client_created_at = time.monotonic()
        return self._client

    def decode_user_token(self, token: str) -> dict[str, Any]:
        signing_key = self._get_client().get_signing_key_from_jwt(token)
        options: dict[str, bool] = {"verify_aud": bool(self._audience)}
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256", "EdDSA"],
            issuer=self._issuer,
            audience=self._audience or None,
            options=options,
        )
