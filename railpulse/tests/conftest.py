"""
Shared pytest fixtures.

Strategy: v0 tests run entirely in-process with ``settings.disable_db=True``.
That flag makes the endpoints skip their DB code paths and makes the rate
limiter use an in-memory counter. The only external dependency that still
needs mocking is the RapidAPI ``PnrClient``.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

# Ensure settings never try to load a real .env from the dev machine.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("RAPIDAPI_KEY", "test-key")


@pytest.fixture(autouse=True)
def _reset_rate_limit_state() -> Iterator[None]:
    from app.api.rate_limit import reset_inmemory_counts

    reset_inmemory_counts()
    yield
    reset_inmemory_counts()


@pytest.fixture
def app_with_disabled_db() -> Iterator[Any]:
    """
    Build a FastAPI app with settings.disable_db forced to True and the DB
    session dependency overridden to yield a no-op session.
    """
    from app.config import get_settings
    from app.db.connection import get_session
    from app.main import create_app

    # Force disable_db on the cached settings singleton.
    settings = get_settings()
    original = settings.disable_db
    settings.disable_db = True

    app = create_app()

    async def _fake_session() -> AsyncIterator[Any]:
        yield None  # handlers skip DB under disable_db

    app.dependency_overrides[get_session] = _fake_session
    try:
        yield app
    finally:
        settings.disable_db = original
        app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_disabled_db: Any) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    with TestClient(app_with_disabled_db) as c:
        yield c
