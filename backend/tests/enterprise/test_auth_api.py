"""Integration tests for the authentication API."""

import time

from .fixtures import create_token_row, query_one, register


def test_register_returns_tokens_and_persists_user(client, db_path):
    data = register(client, email="bob@example.com", username="bob")
    assert "access_token" in data and "refresh_token" in data
    row = query_one(db_path, "SELECT * FROM enterprise_users WHERE email=?", ("bob@example.com",))
    assert row is not None
    assert row["username"] == "bob"
    assert row["is_active"] == 1


def test_register_duplicate_email_conflicts(client, db_path):
    register(client, email="dup@example.com", username="dup1")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "username": "dup2", "password": "password123"},
    )
    assert resp.status_code == 409


def test_login_success_and_header(client, db_path):
    register(client, email="login@example.com", username="login")
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "login@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.headers.get("X-API-Version") == "v1"
    row = query_one(db_path, "SELECT last_login_at FROM enterprise_users WHERE email=?", ("login@example.com",))
    assert row["last_login_at"] is not None


def test_login_with_username_works(client):
    register(client, email="byname@example.com", username="byname")
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "byname", "password": "password123"},
    )
    assert resp.status_code == 200


def test_login_invalid_credentials_rejected(client):
    register(client, email="bad@example.com", username="bad")
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": "bad@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_refresh_rotates_token_pair(client):
    tokens = register(client)
    resp = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert resp.status_code == 200
    new = resp.json()
    assert new["access_token"] != tokens["access_token"]


def test_refresh_invalid_token_rejected(client):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert resp.status_code == 401


def test_logout_is_stateless_ok(client):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200


def test_password_reset_flow(client, db_path):
    register(client, email="reset@example.com", username="reset")
    user = query_one(db_path, "SELECT id FROM enterprise_users WHERE email=?", ("reset@example.com",))
    raw = "reset-token-" + str(int(time.time()))
    create_token_row(db_path, "enterprise_password_reset_tokens", user["id"], raw, ttl=3600)

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "brandnew123"},
    )
    assert confirm.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "reset@example.com", "password": "brandnew123"},
    )
    assert login.status_code == 200

    reused = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw, "new_password": "another123"},
    )
    assert reused.status_code == 400


def test_password_reset_request_does_not_reveal_user(client):
    resp = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200


def test_email_verification_flow(client, db_path):
    register(client, email="verify@example.com", username="verify")
    user = query_one(db_path, "SELECT id FROM enterprise_users WHERE email=?", ("verify@example.com",))
    raw = "verify-token-" + str(int(time.time()))
    create_token_row(db_path, "enterprise_email_verification_tokens", user["id"], raw, ttl=86400)

    resp = client.post("/api/v1/auth/email/verify", json={"token": raw})
    assert resp.status_code == 200
    row = query_one(db_path, "SELECT is_verified FROM enterprise_users WHERE email=?", ("verify@example.com",))
    assert row["is_verified"] == 1


def test_oauth_login_unconfigured_returns_501(client):
    resp = client.get("/api/v1/auth/oauth/google/login")
    assert resp.status_code == 501


def test_email_verification_invalid_token_rejected(client):
    resp = client.post("/api/v1/auth/email/verify", json={"token": "bogus"})
    assert resp.status_code == 400
