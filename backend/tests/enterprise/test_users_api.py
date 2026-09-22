"""Integration tests for the user management API."""

from .fixtures import auth_headers, promote_user, query_one, register


def test_get_me_returns_profile(client, db_path):
    tokens = register(client, email="me@example.com", username="meuser")
    resp = client.get("/api/v1/users/me", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["username"] == "meuser"
    assert "id" in body


def test_update_profile_and_preferences(client, db_path):
    tokens = register(client, email="prof@example.com", username="prof")
    resp = client.patch(
        "/api/v1/users/me",
        headers=auth_headers(tokens["access_token"]),
        json={"full_name": "Prof Name", "preferences": {"theme": "dark"}},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Prof Name"
    row = query_one(
        db_path, "SELECT preferences FROM enterprise_users WHERE email=?", ("prof@example.com",)
    )
    assert "dark" in row["preferences"]


def test_admin_can_list_users(client, db_path):
    tokens = register(client, email="admin@example.com", username="admin")
    promote_user(db_path, "admin@example.com", "admin")
    register(client, email="other@example.com", username="other")

    resp = client.get("/api/v1/users", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert {"admin@example.com", "other@example.com"} <= emails


def test_non_admin_cannot_list_users(client):
    tokens = register(client, email="member@example.com", username="member")
    resp = client.get("/api/v1/users", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 403


def test_admin_can_deactivate_user(client, db_path):
    admin_tokens = register(client, email="boss@example.com", username="boss")
    promote_user(db_path, "boss@example.com", "admin")
    register(client, email="victim@example.com", username="victim")

    victim = query_one(
        db_path, "SELECT id FROM enterprise_users WHERE email=?", ("victim@example.com",)
    )
    resp = client.post(
        f"/api/v1/users/{victim['id']}/deactivate",
        headers=auth_headers(admin_tokens["access_token"]),
    )
    assert resp.status_code == 200
    row = query_one(
        db_path, "SELECT is_active FROM enterprise_users WHERE email=?", ("victim@example.com",)
    )
    assert row["is_active"] == 0


def test_deactivated_user_loses_data_plane_access(client, db_path):
    """Deactivation must revoke access to document/chat/retrieval routes
    immediately (not merely block future refresh)."""
    admin_tokens = register(client, email="gboss@example.com", username="gboss")
    promote_user(db_path, "gboss@example.com", "admin")
    victim_tokens = register(client, email="gvictim@example.com", username="gvictim")

    assert client.get("/api/v1/documents", headers=auth_headers(victim_tokens["access_token"])).status_code == 200

    victim = query_one(
        db_path, "SELECT id FROM enterprise_users WHERE email=?", ("gvictim@example.com",)
    )
    resp = client.post(
        f"/api/v1/users/{victim['id']}/deactivate",
        headers=auth_headers(admin_tokens["access_token"]),
    )
    assert resp.status_code == 200

    for endpoint in ("/api/v1/documents", "/api/v1/chat", "/api/v1/retrieval"):
        r = client.get(endpoint, headers=auth_headers(victim_tokens["access_token"]))
        # 401 = the issued token was revoked server-side; 403 = the account is
        # inactive. Either satisfies "access stops immediately".
        assert r.status_code in (401, 403), endpoint

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": victim_tokens["refresh_token"]},
    )
    assert refresh.status_code in (401, 403)
