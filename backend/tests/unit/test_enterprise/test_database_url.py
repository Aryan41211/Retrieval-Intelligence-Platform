"""Tests for async database URL normalisation.

The enterprise layer runs on SQLAlchemy's asyncio extension. A synchronous
driver URL used to surface as ``InvalidRequestError: The loaded 'pysqlite' is
not async`` deep inside the first authenticated request; these tests pin the
fail-fast/normalise behaviour that replaced it.
"""

import pytest

from backend.enterprise.database import DEFAULT_DATABASE_URL, normalize_database_url


class TestNormalizeDatabaseUrl:
    """Behaviour of :func:`normalize_database_url`."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("sqlite:///./rip.db", "sqlite+aiosqlite:///./rip.db"),
            ("postgresql://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
            ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
            (
                "postgresql+psycopg2://u:p@host/db",
                "postgresql+asyncpg://u:p@host/db",
            ),
            ("mysql://u:p@host/db", "mysql+aiomysql://u:p@host/db"),
        ],
    )
    def test_sync_drivers_are_upgraded_to_async(self, raw: str, expected: str) -> None:
        assert normalize_database_url(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "sqlite+aiosqlite:///./rip.db",
            "postgresql+asyncpg://u:p@host/db",
        ],
    )
    def test_async_drivers_pass_through_unchanged(self, raw: str) -> None:
        assert normalize_database_url(raw) == raw

    def test_default_url_is_already_async(self) -> None:
        assert normalize_database_url(DEFAULT_DATABASE_URL) == DEFAULT_DATABASE_URL

    def test_missing_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="expected a SQLAlchemy URL"):
            normalize_database_url("./rip.db")

    def test_unknown_scheme_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported DATABASE_URL scheme"):
            normalize_database_url("oracle://u:p@host/db")

    def test_credentials_are_preserved(self) -> None:
        """Normalisation must not mangle the credential/query portion."""
        raw = "postgresql://user:p%40ss@host:5432/db?sslmode=require"
        assert normalize_database_url(raw) == (
            "postgresql+asyncpg://user:p%40ss@host:5432/db?sslmode=require"
        )
