"""
OAuth 2.0 login provider support (config-gated).

Implements the authorization-URL and code-exchange flow for Google. The flow is
real but only active when ``ENTERPRISE_OAUTH_ENABLED=true`` and the provider
client credentials are configured. Without credentials the endpoints return
``501 Not Implemented``.
"""

from typing import Any

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
    query = "&".join(f"{k}={v}" for k, v in params.items() if v)
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
        }
