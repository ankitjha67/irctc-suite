"""
App-level rate limiting.

Everyone is "free tier" in v0 (no auth). We identify each caller by a
SHA-256 hash of their IP + the server's SECRET_KEY so the raw IP never
touches the database.

This module exposes two FastAPI dependencies:

    enforce_prediction_rate_limit   — raises 429 when the free-tier daily cap
                                      for predictions is exceeded.
    enforce_track_pnr_rate_limit    — raises 429 when the free-tier cap on
                                      PNRs tracked in a single day is exceeded.

When ``settings.disable_db`` is true (used by the test suite) we fall back to
an in-process counter so the tests can still verify the 429 behavior without
standing up a real Postgres.
"""

from __future__ import annotations

import hashlib
from datetime import date

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.connection import get_session
from app.db.repositories import api_usage


def _hash_ip(ip: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()
    return f"ip:{digest[:32]}"


def get_subject_key(request: Request) -> str:
    """Derive a stable, non-PII subject key from the incoming request."""
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip() or client_ip
    return _hash_ip(client_ip, settings.secret_key)


# In-process fallback counter. Keyed by (subject_key, day, kind).
# Only used when settings.disable_db is True.
_inmemory_counts: dict[tuple[str, date, str], int] = {}


def _bump_inmemory(subject_key: str, kind: str) -> int:
    key = (subject_key, date.today(), kind)
    _inmemory_counts[key] = _inmemory_counts.get(key, 0) + 1
    return _inmemory_counts[key]


def reset_inmemory_counts() -> None:
    """Test hook — clear the in-process counters between tests."""
    _inmemory_counts.clear()


async def enforce_prediction_rate_limit(
    subject_key: str = Depends(get_subject_key),
    session: AsyncSession = Depends(get_session),
) -> str:
    settings = get_settings()

    if settings.disable_db:
        count = _bump_inmemory(subject_key, "predict")
    else:
        count = await api_usage.increment_predictions(session, subject_key=subject_key)

    if count > settings.free_predictions_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Free tier allows {settings.free_predictions_per_day} predictions per day. "
                "Upgrade to Pro for higher limits."
            ),
        )
    return subject_key


async def enforce_track_pnr_rate_limit(
    subject_key: str = Depends(get_subject_key),
    session: AsyncSession = Depends(get_session),
) -> str:
    settings = get_settings()

    if settings.disable_db:
        count = _bump_inmemory(subject_key, "track")
    else:
        count = await api_usage.increment_tracked_pnrs(session, subject_key=subject_key)

    if count > settings.free_tracked_pnrs:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Free tier allows tracking {settings.free_tracked_pnrs} PNRs per day. "
                "Upgrade to Pro for higher limits."
            ),
        )
    return subject_key
