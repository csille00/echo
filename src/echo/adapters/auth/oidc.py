"""Generic OpenID Connect login (authorization code + PKCE).

Any issuer that publishes a discovery document can be used. The app validates
the ID token and then issues its own session cookie.
"""

import base64
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from echo.adapters.auth.jwks import JwksValidator
from echo.adapters.db.users import (
    UserRecord,
    count_users,
    get_user_by_email,
    get_user_by_id,
    get_user_by_oidc,
    insert_user,
    link_oidc,
    lock_registration,
)
from echo.config import Settings, get_settings

logger = logging.getLogger(__name__)

_DISCOVERY_TTL_SECONDS = 3600
_discovery_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class OidcError(Exception):
    """A sign-in failure safe to show to the user."""


@dataclass(frozen=True)
class OidcProfile:
    """Identity claims used to find or create a local account."""

    issuer: str
    subject: str
    email: str
    name: str


def code_challenge(verifier: str) -> str:
    """S256 PKCE challenge for a verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def authorization_redirect(
    authorize_endpoint: str,
    *,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    nonce: str,
    verifier: str,
) -> str:
    """Build the browser redirect to the provider's authorization endpoint."""
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    separator = "&" if "?" in authorize_endpoint else "?"
    return f"{authorize_endpoint}{separator}{query}"


def profile_from_claims(
    issuer: str,
    id_claims: dict[str, Any],
    userinfo: dict[str, Any] | None = None,
) -> OidcProfile:
    """Merge an ID token and optional userinfo into an email and display name."""
    claims = dict(id_claims)
    if userinfo:
        for key, value in userinfo.items():
            if key not in claims or claims[key] in (None, ""):
                claims[key] = value

    subject = _required_claim(
        claims,
        "sub",
        "The identity provider did not send a subject identifier",
    )
    email = _required_claim(
        claims,
        "email",
        "The identity provider did not send an email address",
    )
    return OidcProfile(
        issuer=issuer,
        subject=subject,
        email=email.lower(),
        name=_display_name(claims, email.lower()),
    )


def _required_claim(claims: dict[str, Any], key: str, missing: str) -> str:
    text = _claim_str(claims, key)
    if text is None:
        raise OidcError(missing)
    return text


def _claim_str(claims: dict[str, Any], key: str) -> str | None:
    """Read one claim. Every JSON type is handled."""
    match claims.get(key):
        case str(text):
            stripped = text.strip()
            return stripped or None
        case None:
            return None
        case _:
            raise OidcError(f"The identity provider sent {key} in an unexpected form")


def _display_name(claims: dict[str, Any], email: str) -> str:
    for key in ("name", "preferred_username", "given_name"):
        text = _claim_str(claims, key)
        if text is not None:
            return text
    local, separator, _domain = email.partition("@")
    if separator and local:
        return local
    raise OidcError("The identity provider did not send a name")


async def fetch_discovery(issuer: str) -> dict[str, Any]:
    """Load and cache the provider's discovery document."""
    now = time.monotonic()
    cached = _discovery_cache.get(issuer)
    if cached is not None and now - cached[0] < _DISCOVERY_TTL_SECONDS:
        return cached[1]

    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(url)
        response.raise_for_status()
        document = response.json()
    if not isinstance(document, dict):
        raise OidcError("Identity provider discovery document was not valid")
    _discovery_cache[issuer] = (now, document)
    return document


async def exchange_code(
    settings: Settings,
    *,
    code: str,
    redirect_uri: str,
    nonce: str,
    verifier: str,
) -> OidcProfile:
    """Trade an authorization code for a validated profile."""
    if not settings.oidc_issuer or not settings.oidc_client_id:
        raise OidcError("OIDC is not configured")
    discovery = await fetch_discovery(settings.oidc_issuer)
    token_endpoint = discovery.get("token_endpoint")
    if not isinstance(token_endpoint, str) or not token_endpoint:
        raise OidcError("Identity provider did not publish a token endpoint")

    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret.get_secret_value(),
        "code_verifier": verifier,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(token_endpoint, data=form)
        if token_response.status_code >= 400:
            logger.warning("OIDC token endpoint returned %s", token_response.status_code)
            raise OidcError("The identity provider rejected the sign-in")
        token_body = token_response.json()
        if not isinstance(token_body, dict):
            raise OidcError("The identity provider rejected the sign-in")
        id_token = token_body.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise OidcError("The identity provider did not return an ID token")

        jwks_uri = settings.oidc_jwks_url or discovery.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise OidcError("Identity provider did not publish a JWKS URI")
        issuer = discovery.get("issuer")
        expected_issuer = issuer if isinstance(issuer, str) and issuer else settings.oidc_issuer
        validator = JwksValidator(
            jwks_uri,
            issuer=expected_issuer,
            audience=settings.oidc_audience or settings.oidc_client_id,
        )
        try:
            claims = validator.decode_user_token(id_token)
        except Exception as exc:
            logger.warning("OIDC ID token rejected: %s", exc)
            raise OidcError("The identity provider token could not be verified") from exc

        token_nonce = claims.get("nonce")
        if token_nonce != nonce:
            raise OidcError("The identity provider token could not be verified")

        userinfo: dict[str, Any] | None = None
        if _claim_str(claims, "email") is None:
            userinfo = await _fetch_userinfo(client, discovery, token_body.get("access_token"))

    return profile_from_claims(expected_issuer, claims, userinfo)


async def _fetch_userinfo(
    client: httpx.AsyncClient,
    discovery: dict[str, Any],
    access_token: object,
) -> dict[str, Any] | None:
    endpoint = discovery.get("userinfo_endpoint")
    if not isinstance(endpoint, str) or not isinstance(access_token, str) or not access_token:
        return None
    response = await client.get(endpoint, headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        return None
    body = response.json()
    return body if isinstance(body, dict) else None


def _subject_uuid(subject: str) -> UUID | None:
    """Return the subject when it is a UUID so an existing account id can be reused."""
    try:
        return UUID(subject)
    except ValueError:
        return None


def _identity_conflict(user: UserRecord, profile: OidcProfile) -> bool:
    if not user.oidc_subject:
        return False
    return user.oidc_subject != profile.subject or user.oidc_issuer != profile.issuer


async def _use_existing(
    session: AsyncSession,
    user: UserRecord,
    profile: OidcProfile,
) -> UserRecord:
    if _identity_conflict(user, profile):
        raise OidcError("That sign-in is already linked to a different account")
    if not user.oidc_subject:
        await link_oidc(session, user.id, profile.issuer, profile.subject)
    return await _reload(session, user.id)


async def provision_oidc_user(session: AsyncSession, profile: OidcProfile) -> UserRecord:
    """Find or create the local account for an OIDC profile.

    A UUID subject is reused as the account id, so rows already stored under
    that id stay with this person. Any other subject gets a new account id.
    """
    await lock_registration(session)
    linked = await get_user_by_oidc(session, profile.issuer, profile.subject)
    if linked is not None:
        return linked

    by_email = await get_user_by_email(session, profile.email)
    if by_email is not None:
        return await _use_existing(session, by_email, profile)

    adopted_id = _subject_uuid(profile.subject)
    existing = await get_user_by_id(session, adopted_id) if adopted_id is not None else None
    if existing is not None:
        return await _use_existing(session, existing, profile)

    if not get_settings().oidc_auto_register:
        raise OidcError("No account for this sign-in. Ask an admin to create one.")

    is_admin = await count_users(session) == 0
    return await insert_user(
        session,
        email=profile.email,
        name=profile.name,
        password_hash=None,
        is_admin=is_admin,
        user_id=adopted_id,
        oidc_issuer=profile.issuer,
        oidc_subject=profile.subject,
    )


async def _reload(session: AsyncSession, user_id: UUID) -> UserRecord:
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise OidcError("Could not load the account for this sign-in")
    return user
