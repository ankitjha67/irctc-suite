"""
Async SQLAlchemy session factory.

The FastAPI service uses a single engine configured from DATABASE_URL. The URL
can be supplied with either a sync driver (``postgresql+psycopg://...``) or an
async driver (``postgresql+asyncpg://...``) — we normalize to asyncpg since
that's what the Supabase pooler tolerates best.

A small abstraction here (``get_session`` dependency) keeps the endpoints
clean while still letting tests override the engine via ``override_engine``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


def _normalize_async_url(url: str) -> str:
    """Coerce a sync SQLAlchemy URL into an async one for asyncpg."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql+psycopg://"):
        return "postgresql+asyncpg://" + url[len("postgresql+psycopg://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    url = _normalize_async_url(settings.database_url)
    logger.info("Building async engine for %s", _mask_password(url))
    # pool_pre_ping guards against stale pooled connections from Supabase.
    return create_async_engine(url, pool_pre_ping=True, future=True)


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = _build_engine()
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        get_engine()
    assert _sessionmaker is not None
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields one session per request."""
    maker = get_sessionmaker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def override_engine(engine: AsyncEngine | None, sessionmaker: Any = None) -> None:
    """Test hook — swap the module-level engine/sessionmaker."""
    global _engine, _sessionmaker
    _engine = engine
    _sessionmaker = sessionmaker


def _mask_password(url: str) -> str:
    try:
        scheme, rest = url.split("://", 1)
        if "@" not in rest:
            return url
        creds, host = rest.split("@", 1)
        if ":" not in creds:
            return url
        user, _ = creds.split(":", 1)
        return f"{scheme}://{user}:***@{host}"
    except Exception:
        return url
