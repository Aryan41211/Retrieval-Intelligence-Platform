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


class Base(DeclarativeBase):
    """Declarative base for enterprise ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _resolve_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


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


async def init_db() -> None:
    """Create all enterprise tables. Import models so they register on ``Base``."""
    from backend.enterprise import models  # noqa: F401 - ensure models are registered

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
