"""Tests for generic OIDC helpers."""

import pytest

from journal_search.adapters.auth.oidc import (
    OidcError,
    authorization_redirect,
    code_challenge,
    profile_from_claims,
)
from journal_search.config import Settings


def test_code_challenge_is_unpadded_s256() -> None:
    challenge = code_challenge("verifier")
    assert "=" not in challenge
    assert len(challenge) > 20


def test_authorization_redirect_includes_pkce() -> None:
    url = authorization_redirect(
        "https://idp.example/authorize",
        client_id="journal",
        redirect_uri="https://journal.example/api/v1/auth/oidc/callback",
        scope="openid profile email",
        state="state",
        nonce="nonce",
        verifier="verifier",
    )
    assert url.startswith("https://idp.example/authorize?")
    assert "code_challenge_method=S256" in url
    assert "client_id=journal" in url
    assert f"code_challenge={code_challenge('verifier')}" in url


def test_profile_fills_email_from_userinfo() -> None:
    profile = profile_from_claims(
        "https://idp.example",
        {"sub": "abc", "nonce": "n"},
        {"email": "Ada@Example.com", "name": "Ada"},
    )
    assert profile.email == "ada@example.com"
    assert profile.name == "Ada"
    assert profile.subject == "abc"
    assert profile.issuer == "https://idp.example"


def test_profile_requires_email() -> None:
    with pytest.raises(OidcError):
        profile_from_claims("https://idp.example", {"sub": "abc"}, None)


def test_oidc_enabled_requires_client_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET"):
        monkeypatch.delenv(key, raising=False)
    common = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "oidc_issuer": "https://idp.example",
        "oidc_client_id": "journal",
    }
    disabled = Settings(_env_file=None, oidc_client_secret="", **common)  # type: ignore[call-arg]
    enabled = Settings(_env_file=None, oidc_client_secret="secret", **common)  # type: ignore[call-arg]
    assert disabled.oidc_enabled is False
    assert enabled.oidc_enabled is True
