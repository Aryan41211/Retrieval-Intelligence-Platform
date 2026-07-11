"""Test fixtures for enterprise feature tests.

Provides an isolated SQLite database and a FastAPI ``TestClient`` wired to the
real application. The database file is unique per test, so tests never interfere
with each other.
"""

import os
from collections.abc import Iterator
from pathlib import Path

# Configure enterprise test settings BEFORE any backend module is imported so
# the lru-cached settings pick up deterministic values.
os.environ.setdefault("ENTERPRISE_ENVIRONMENT", "development")
os.environ.setdefault("ENTERPRISE_JWT_SECRET_KEY", "test-secret-key-not-for-prod-use-1234567890")
os.environ.setdefault("ENTERPRISE_REGISTRATION_ENABLED", "true")
os.environ.setdefault("ENTERPRISE_EMAIL_VERIFICATION_REQUIRED", "false")
os.environ.setdefault("API_RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient

import backend.enterprise.database as enterprise_database


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Return a unique database file path for the test and reset the engine."""
    path = str(tmp_path / "rip_enterprise.db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path}"
    # Reset the module-level engine/session factory synchronously so the next
    # get_engine() rebuilds against the freshly configured DATABASE_URL in the
    # current event loop (TestClient runs each test in its own loop).
    enterprise_database._engine = None
    enterprise_database._session_factory = None
    return path


@pytest.fixture()
def client(db_path: str) -> Iterator[TestClient]:
    """Yield a TestClient bound to an isolated enterprise database."""
    from backend.api.app import app

    with TestClient(app) as test_client:
        yield test_client
