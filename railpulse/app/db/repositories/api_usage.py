"""
Rate-limit counters — per-subject-per-day.

``subject_key`` is either a user id or an ``ip:<sha256>`` hash. We pack both
into a single text column so the primary key stays simple.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def increment_predictions(
    session: AsyncSession,
    *,
    subject_key: str,
    day: date | None = None,
) -> int:
    """Atomically bump prediction_count and return the new value."""
    d = day or date.today()
    result = await session.execute(
        text(
            """
            INSERT INTO railpulse.api_usage (subject_key, day, prediction_count)
            VALUES (:subject_key, :day, 1)
            ON CONFLICT (subject_key, day) DO UPDATE
              SET prediction_count = railpulse.api_usage.prediction_count + 1
            RETURNING prediction_count
            """
        ),
        {"subject_key": subject_key, "day": d},
    )
    value = result.scalar()
    return int(value) if value is not None else 1


async def increment_tracked_pnrs(
    session: AsyncSession,
    *,
    subject_key: str,
    day: date | None = None,
) -> int:
    d = day or date.today()
    result = await session.execute(
        text(
            """
            INSERT INTO railpulse.api_usage (subject_key, day, tracked_pnr_count)
            VALUES (:subject_key, :day, 1)
            ON CONFLICT (subject_key, day) DO UPDATE
              SET tracked_pnr_count = railpulse.api_usage.tracked_pnr_count + 1
            RETURNING tracked_pnr_count
            """
        ),
        {"subject_key": subject_key, "day": d},
    )
    value = result.scalar()
    return int(value) if value is not None else 1


async def get_usage(
    session: AsyncSession,
    *,
    subject_key: str,
    day: date | None = None,
) -> tuple[int, int]:
    d = day or date.today()
    result = await session.execute(
        text(
            """
            SELECT prediction_count, tracked_pnr_count
            FROM railpulse.api_usage
            WHERE subject_key = :subject_key AND day = :day
            """
        ),
        {"subject_key": subject_key, "day": d},
    )
    row = result.first()
    if row is None:
        return 0, 0
    return int(row[0] or 0), int(row[1] or 0)
