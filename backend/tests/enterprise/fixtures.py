"""Shared helpers for enterprise API tests (sync DB writes/reads, auth helpers)."""

import sqlite3
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.enterprise import security


def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def query_one(db_path: str, sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Run a SELECT and return the first row (sync, for test assertions)."""
    conn = _conn(db_path)
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def query_all(db_path: str, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a SELECT and return all rows (sync, for test assertions)."""
    conn = _conn(db_path)
    try:
        return list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def promote_user(db_path: str, email: str, role: str) -> None:
    """Promote a user to a given role via a direct sync DB write."""
    conn = _conn(db_path)
    try:
        conn.execute("UPDATE enterprise_users SET role=? WHERE email=?", (role, email))
        conn.commit()
    finally:
        conn.close()


def create_token_row(
    db_path: str, table: str, user_id: str, raw_token: str, ttl: int = 3600
) -> None:
    """Insert a password-reset / email-verification token row directly.

    Uses naive UTC timestamps to match the application's storage convention.
    """
    expires = datetime.utcnow() + timedelta(seconds=ttl)
    conn = _conn(db_path)
    try:
        conn.execute(
            f"INSERT INTO {table} (id, user_id, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                f"tok-{raw_token}",
                user_id,
                security.hash_token(raw_token),
                expires,
                datetime.utcnow(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def auth_headers(token: str) -> dict:
    """Return Authorization headers for a bearer token."""
    return {"Authorization": f"Bearer {token}"}


def register(
    client: TestClient,
    email: str = "alice@example.com",
    username: str = "alice",
    password: str = "password123",
) -> dict:
    """Register a user and return the parsed token response."""
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
