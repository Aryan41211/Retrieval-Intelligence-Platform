"""
OAuth 2.0 login provider support (config-gated).

Implements the authorization-URL and code-exchange flow for Google. The flow is
real but only active when ``ENTERPRISE_OAUTH_ENABLED=true`` and the provider
client credentials are configured. Without credentials the endpoints return
``501 Not Implemented``.
"""

import time
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.enterprise.config import get_enterprise_settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

_SUPPORTED = {"google"}


def is_oauth_configured(provider: str) -> bool:
    """Return True if a provider is enabled and configured."""
    settings = get_enterprise_settings()
    if not settings.oauth_enabled or provider not in _SUPPORTED:
        return False
    return bool(settings.oauth_google_client_id and settings.oauth_google_client_secret)


# In-process store of issued OAuth state values -> expiry timestamp. Single
# process only; a multi-instance deployment must move this to Redis alongside
# the rate limiter. Entries are single-use and short-lived.
_OAUTH_STATE_TTL_SECONDS = 600
_issued_states: dict[str, float] = {}


def _purge_expired_states(now: float) -> None:
    for value, expires_at in list(_issued_states.items()):
        if expires_at <= now:
            _issued_states.pop(value, None)


def remember_state(state: str) -> None:
    """Record an issued OAuth state so the callback can verify it."""
    now = time.time()
    _purge_expired_states(now)
    _issued_states[state] = now + _OAUTH_STATE_TTL_SECONDS


def consume_state(state: str | None) -> bool:
    """Validate and single-use-consume an OAuth state value.

    Args:
        state: The ``state`` query parameter returned by the provider.

    Returns:
        True if the state was issued by us and has not expired or been used.
    """
    if not state:
        return False
    now = time.time()
    _purge_expired_states(now)
    expires_at = _issued_states.pop(state, None)
    return expires_at is not None and expires_at > now


def get_authorization_url(provider: str, state: str) -> str:
    """Build the provider authorization URL for the given CSRF state."""
    settings = get_enterprise_settings()
    if provider != "google":
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    params = {
        "client_id": settings.oauth_google_client_id,
        "redirect_uri": settings.oauth_google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    # urlencode, not manual join: redirect_uri contains ':' and '/' and was
    # previously emitted raw into the query string.
    query = urlencode({k: v for k, v in params.items() if v})
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code(provider: str, code: str) -> dict[str, Any]:
    """Exchange an authorization code for the user's profile info."""
    settings = get_enterprise_settings()
    if provider != "google":
        raise ValueError(f"Unsupported OAuth provider: {provider}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.oauth_google_client_id,
                "client_secret": settings.oauth_google_client_secret,
                "redirect_uri": settings.oauth_google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]
        user_resp = await client.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        user_resp.raise_for_status()
        data = user_resp.json()
        return {
            "email": data.get("email"),
            "full_name": data.get("name", ""),
            # Google returns email_verified; without checking it an attacker can
            # register an unverified address matching an existing local account.
            "email_verified": bool(data.get("email_verified", False)),
            "subject": data.get("sub"),
        }
