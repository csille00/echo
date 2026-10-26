"""Browser login against any OpenID Connect provider."""

import logging
import secrets
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from journal_search.adapters.auth.cookies import (
    OIDC_NONCE_COOKIE,
    OIDC_STATE_COOKIE,
    OIDC_VERIFIER_COOKIE,
)
from journal_search.adapters.auth.oidc import (
    OidcError,
    authorization_redirect,
    exchange_code,
    fetch_discovery,
    provision_oidc_user,
)
from journal_search.adapters.db.users import create_session
from journal_search.api.routes.auth import _set_session_cookie
from journal_search.config import get_settings
from journal_search.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oidc", tags=["auth"])

_COOKIE_MAX_AGE = 600


def redirect_uri(request: Request) -> str:
    """Callback URL registered on the OIDC client."""
    settings = get_settings()
    if settings.public_url.strip():
        base = settings.public_url.strip().rstrip("/")
    else:
        base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/oidc/callback"


def _stash_cookie(response: RedirectResponse, name: str, value: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=name,
        value=value,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_oidc_cookies(response: RedirectResponse) -> None:
    for name in (OIDC_STATE_COOKIE, OIDC_VERIFIER_COOKIE, OIDC_NONCE_COOKIE):
        response.delete_cookie(name, path="/")


def _fail(message: str) -> RedirectResponse:
    response = RedirectResponse(f"/login?error={quote(message)}", status_code=302)
    _clear_oidc_cookies(response)
    return response


@router.get("/start")
async def oidc_start(request: Request) -> RedirectResponse:
    """Send the browser to the configured identity provider."""
    settings = get_settings()
    if not settings.oidc_enabled:
        return _fail("SSO is not configured")
    try:
        discovery = await fetch_discovery(settings.oidc_issuer)
    except Exception:
        logger.exception("OIDC discovery failed")
        return _fail("Could not reach the identity provider")
    authorize = discovery.get("authorization_endpoint")
    if not isinstance(authorize, str) or not authorize:
        return _fail("Identity provider did not publish an authorization endpoint")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    location = authorization_redirect(
        authorize,
        client_id=settings.oidc_client_id,
        redirect_uri=redirect_uri(request),
        scope=settings.oidc_scopes,
        state=state,
        nonce=nonce,
        verifier=verifier,
    )
    response = RedirectResponse(location, status_code=302)
    _stash_cookie(response, OIDC_STATE_COOKIE, state)
    _stash_cookie(response, OIDC_NONCE_COOKIE, nonce)
    _stash_cookie(response, OIDC_VERIFIER_COOKIE, verifier)
    return response


@router.get("/callback")
async def oidc_callback(request: Request) -> RedirectResponse:
    """Finish sign-in and set the app session cookie."""
    settings = get_settings()
    if not settings.oidc_enabled:
        return _fail("SSO is not configured")
    if request.query_params.get("error"):
        return _fail("The identity provider denied the sign-in")

    state = request.cookies.get(OIDC_STATE_COOKIE)
    nonce = request.cookies.get(OIDC_NONCE_COOKIE)
    verifier = request.cookies.get(OIDC_VERIFIER_COOKIE)
    code = request.query_params.get("code")
    returned_state = request.query_params.get("state")
    if not state or not nonce or not verifier or not code or returned_state != state:
        return _fail("SSO sign-in could not be verified. Try again.")

    try:
        profile = await exchange_code(
            settings,
            code=code,
            redirect_uri=redirect_uri(request),
            nonce=nonce,
            verifier=verifier,
        )
        async with get_session() as session:
            user = await provision_oidc_user(session, profile)
            token = await create_session(session, user.id, settings.session_ttl_days)
            await session.commit()
    except OidcError as exc:
        return _fail(str(exc))
    except Exception:
        logger.exception("OIDC callback failed")
        return _fail("Could not sign in with SSO")

    response = RedirectResponse("/", status_code=302)
    _set_session_cookie(response, token)
    _clear_oidc_cookies(response)
    return response
