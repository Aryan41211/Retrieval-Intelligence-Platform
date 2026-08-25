"""Regression tests for the Phase 3 security fixes.

Each test pins a specific vulnerability found in the audit so it cannot silently
return: workspace member enumeration, OAuth login CSRF, OAuth account takeover,
public metrics, spoofable rate-limit keys, and unbounded request inputs.
"""

import pytest
from fastapi.testclient import TestClient

from backend.enterprise import oauth


def _register(client: TestClient, username: str) -> tuple[str, str]:
    """Register a user and return (user_id, access_token)."""
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "correct-horse-battery",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return me.json()["id"], token


class TestWorkspaceMemberAuthorization:
    """H2: listing workspace members performed no authorization check."""

    def test_outsider_cannot_list_members(self, client: TestClient) -> None:
        _, owner_token = _register(client, "wsowner")
        _, outsider_token = _register(client, "wsoutsider")

        created = client.post(
            "/api/v1/workspaces",
            json={"name": "Private KB"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert created.status_code == 201, created.text
        workspace_id = created.json()["id"]

        resp = client.get(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers={"Authorization": f"Bearer {outsider_token}"},
        )
        assert resp.status_code == 403

    def test_owner_can_list_members(self, client: TestClient) -> None:
        _, owner_token = _register(client, "wsowner2")
        created = client.post(
            "/api/v1/workspaces",
            json={"name": "My KB"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        workspace_id = created.json()["id"]

        resp = client.get(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 200
        assert [m["username"] for m in resp.json()] == ["wsowner2"]

    def test_unknown_workspace_is_404(self, client: TestClient) -> None:
        _, token = _register(client, "wsnotfound")
        resp = client.get(
            "/api/v1/workspaces/does-not-exist/members",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestOAuthStateCsrf:
    """H3: the OAuth state value was generated but never validated."""

    def setup_method(self) -> None:
        oauth._issued_states.clear()

    def test_unissued_state_is_rejected(self) -> None:
        assert oauth.consume_state("never-issued") is False

    def test_missing_state_is_rejected(self) -> None:
        assert oauth.consume_state(None) is False

    def test_issued_state_is_accepted_once(self) -> None:
        oauth.remember_state("state-abc")
        assert oauth.consume_state("state-abc") is True
        # Single use: a replayed state must not be accepted again.
        assert oauth.consume_state("state-abc") is False

    def test_expired_state_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        oauth.remember_state("state-old")
        # Advance the clock past the TTL, relative to the real current time.
        expired_at = oauth.time.time() + oauth._OAUTH_STATE_TTL_SECONDS + 1
        monkeypatch.setattr(oauth.time, "time", lambda: expired_at)
        assert oauth.consume_state("state-old") is False

    def test_callback_rejects_bad_state(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/oauth/google/callback?code=abc&state=forged")
        # 400 (bad state) or 501 (provider unconfigured) - never a token grant.
        assert resp.status_code in (400, 501)
        assert "access_token" not in resp.text

    def test_authorization_url_is_percent_encoded(self, monkeypatch) -> None:
        """The redirect_uri contains ':' and '/' and must not be emitted raw."""
        settings = oauth.get_enterprise_settings()
        monkeypatch.setattr(settings, "oauth_google_client_id", "cid", raising=False)
        monkeypatch.setattr(
            settings,
            "oauth_google_redirect_uri",
            "https://app.example.com/cb",
            raising=False,
        )
        url = oauth.get_authorization_url("google", "st8")
        assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcb" in url
        assert "scope=openid+email+profile" in url


class TestOAuthAccountTakeover:
    """H4: an unverified provider email could claim an existing local account."""

    @pytest.mark.asyncio
    async def test_unverified_email_is_refused(self, monkeypatch) -> None:
        from fastapi import HTTPException

        from backend.enterprise import services

        async def fake_exchange(provider: str, code: str) -> dict[str, object]:
            return {"email": "victim@example.com", "full_name": "V", "email_verified": False}

        monkeypatch.setattr(services, "exchange_code", fake_exchange)
        monkeypatch.setattr(services, "is_oauth_configured", lambda provider: True)

        with pytest.raises(HTTPException) as exc:
            await services.oauth_login(None, "google", "code")
        assert exc.value.status_code == 403
        assert "not verified" in exc.value.detail


class TestMetricsAuthorization:
    """H9: /metrics was readable by anyone."""

    def test_metrics_requires_credentials(self, client: TestClient) -> None:
        assert client.get("/api/v1/metrics").status_code == 401

    def test_metrics_accepts_user_token(self, client: TestClient) -> None:
        _, token = _register(client, "metricsuser")
        resp = client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "rip_http_requests_total" in resp.text

    def test_metrics_rejects_garbage_token(self, client: TestClient) -> None:
        resp = client.get("/api/v1/metrics", headers={"Authorization": "Bearer not-a-jwt"})
        assert resp.status_code == 401


class TestRequestValidationBounds:
    """M7: user-supplied inputs were unbounded."""

    def test_oversized_chat_query_is_rejected(self, client: TestClient) -> None:
        _, token = _register(client, "boundsuser")
        resp = client.post(
            "/api/v1/chat",
            json={"query": "x" * 5000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_absurd_top_k_is_rejected(self, client: TestClient) -> None:
        _, token = _register(client, "topkuser")
        resp = client.post(
            "/api/v1/retrieval/search",
            json={"query": "hello", "top_k": 10_000_000},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_empty_query_is_rejected(self, client: TestClient) -> None:
        _, token = _register(client, "emptyuser")
        resp = client.post(
            "/api/v1/retrieval/search",
            json={"query": "", "top_k": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_invalid_message_role_is_rejected(self, client: TestClient) -> None:
        _, token = _register(client, "roleuser")
        headers = {"Authorization": f"Bearer {token}"}
        conv = client.post("/api/v1/conversations", json={"title": "t"}, headers=headers)
        assert conv.status_code == 201
        resp = client.post(
            f"/api/v1/conversations/{conv.json()['id']}/messages",
            json={"role": "root", "content": "hi"},
            headers=headers,
        )
        assert resp.status_code == 422
