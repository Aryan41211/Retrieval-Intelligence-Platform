"""
Async database layer for enterprise features.

Uses SQLAlchemy 2.0 async with a configurable URL (``DATABASE_URL``). Tables are
created on startup via :func:`init_db`; for tests, point ``DATABASE_URL`` at a
temporary SQLite file and call :func:`init_db` in a fixture.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./rip.db"

# The enterprise layer runs on SQLAlchemy's asyncio extension, which refuses any
# synchronous DBAPI driver. Operators (and our own .env / docker-compose files)
# naturally write the familiar sync form, so map the well-known sync drivers onto
# their async equivalents instead of failing deep inside the first request with
# "The loaded 'pysqlite' is not async".
_ASYNC_DRIVER_BY_SYNC_SCHEME = {
    "sqlite": "sqlite+aiosqlite",
    "postgresql": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
    "postgresql+psycopg2": "postgresql+asyncpg",
    "mysql": "mysql+aiomysql",
}


class Base(DeclarativeBase):
    """Declarative base for enterprise ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_database_url(url: str) -> str:
    """Return an asyncio-compatible SQLAlchemy URL.

    Args:
        url: Raw database URL, possibly naming a synchronous driver.

    Returns:
        The same URL with a synchronous driver upgraded to its async equivalent.

    Raises:
        ValueError: If the URL has no scheme, or names a driver with no known
            async counterpart, so misconfiguration fails fast and legibly.
    """
    if "://" not in url:
        raise ValueError(
            f"Invalid DATABASE_URL {url!r}: expected a SQLAlchemy URL such as "
            "'postgresql+asyncpg://user:pass@host/db' or 'sqlite+aiosqlite:///./rip.db'."
        )
    scheme, remainder = url.split("://", 1)
    if "+" in scheme:
        # Already driver-qualified; only remap known-sync drivers (e.g. psycopg2).
        replacement = _ASYNC_DRIVER_BY_SYNC_SCHEME.get(scheme)
        if replacement is None:
            return url
        return f"{replacement}://{remainder}"

    replacement = _ASYNC_DRIVER_BY_SYNC_SCHEME.get(scheme)
    if replacement is None:
        raise ValueError(
            f"Unsupported DATABASE_URL scheme {scheme!r}. The enterprise layer requires an "
            "async driver; supported forms are "
            f"{', '.join(sorted(_ASYNC_DRIVER_BY_SYNC_SCHEME))} or an explicit '+driver' URL."
        )
    return f"{replacement}://{remainder}"


def _resolve_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def get_engine() -> AsyncEngine:
    """Return the active async engine, creating it on first use."""
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(_resolve_database_url(), echo=False, future=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, initialising the engine if needed."""
    get_engine()
    assert _session_factory is not None
    return _session_factory


def _auto_create_enabled() -> bool:
    """Return True when the app may create tables itself.

    Alembic owns the schema in any deployment that can outlive a single release
    (`alembic upgrade head` runs from the container entrypoint). ``create_all``
    remains the default for local development and tests, where a throwaway
    SQLite file is created from scratch. Set ``DB_AUTO_CREATE=false`` wherever
    migrations are authoritative so the two cannot disagree.
    """
    return os.environ.get("DB_AUTO_CREATE", "true").strip().lower() not in {
        "false",
        "0",
        "no",
    }


async def init_db() -> None:
    """Create enterprise tables unless migrations own the schema."""
    from backend.enterprise import models  # noqa: F401 - ensure models are registered

    if not _auto_create_enabled():
        return

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose the engine (used in tests / shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a session within a transaction, committing on success."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async session that commits on success.

    Mirrors :func:`session_scope` so router writes are persisted and rolled back
    on error, instead of being silently discarded when the session closes.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
