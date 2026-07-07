"""Test fixtures for enterprise feature tests.

Provides an isolated SQLite database and a FastAPI ``TestClient`` wired to the
real application. The database file is unique per test, so tests never interfere
with each other.
"""

import os
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
