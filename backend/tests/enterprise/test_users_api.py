"""Integration tests for the user management API."""

from .conftest import auth_headers, promote_user, query_one, register


def test_get_me_returns_profile(client, db_path):
    tokens = register(client, email="me@example.com", username="me")
    resp = client.get("/api/v1/users/me", headers=auth_headers(tokens["access_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@example.com"
    assert body["username"] == "me"
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
    row = query_one(db_path, "SELECT preferences FROM enterprise_users WHERE email=?", ("prof@example.com",))
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

    victim = query_one(db_path, "SELECT id FROM enterprise_users WHERE email=?", ("victim@example.com",))
    resp = client.post(
        f"/api/v1/users/{victim['id']}/deactivate",
        headers=auth_headers(admin_tokens["access_token"]),
    )
    assert resp.status_code == 200
    row = query_one(db_path, "SELECT is_active FROM enterprise_users WHERE email=?", ("victim@example.com",))
    assert row["is_active"] == 0
