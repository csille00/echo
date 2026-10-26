"""Shared async database engine and session factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from echo.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings | None = None) -> None:
    """Create the shared async engine and session factory."""
    global _engine, _session_factory
    settings = settings or get_settings()
    _engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    """Return the shared async engine."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() during app startup.")
    return _engine


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session from the shared pool."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() during app startup.")
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    """Dispose the shared engine."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
