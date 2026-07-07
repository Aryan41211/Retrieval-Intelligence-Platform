"""Test fixtures and helpers for enterprise feature tests.

Provides an isolated SQLite database and a FastAPI ``TestClient`` wired to the
real application. The database file is unique per test, so tests never interfere
with each other. Direct DB assertions and role promotion are performed with a
synchronous ``sqlite3`` connection to the same file, avoiding async event-loop
sharing issues.
"""

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

# Configure enterprise test settings BEFORE any backend module is imported so
# the lru-cached settings pick up deterministic values.
os.environ.setdefault("ENTERPRISE_ENVIRONMENT", "development")
os.environ.setdefault("ENTERPRISE_JWT_SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("ENTERPRISE_REGISTRATION_ENABLED", "true")
os.environ.setdefault("ENTERPRISE_EMAIL_VERIFICATION_REQUIRED", "false")

import pytest
from fastapi.testclient import TestClient

from backend.enterprise.database import dispose_db


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Return a unique database file path for the test and reset the engine."""
    path = str(tmp_path / "rip_enterprise.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    # Force the module-level engine/session factory to be rebuilt against the
    # freshly configured DATABASE_URL.
    dispose_db()
    return path


@pytest.fixture()
def client(db_path: str) -> Iterator[TestClient]:
    """Yield a TestClient bound to an isolated enterprise database."""
    from backend.api.app import app

    with TestClient(app) as test_client:
        yield test_client


def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def query_one(db_path: str, sql: str, params: tuple = ()) -> sqlite3.Row | None:
    """Run a SELECT and return the first row (sync, for test assertions)."""
    conn = _conn(db_path)
    try:
        row = conn.execute(sql, params).fetchone()
        return row
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


def auth_headers(token: str) -> dict:
    """Return Authorization headers for a bearer token."""
    return {"Authorization": f"Bearer {token}"}
