"""
Trains reference repository — lazy seeding when we see a new train number.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Known premium trains for day-1 priors on the heuristic.
# This is a small hand-curated starter set; scripts/seed_trains.py can grow it.
PREMIUM_TRAIN_PREFIXES = (
    "12951", "12952",  # Mumbai Rajdhani
    "12953", "12954",  # August Kranti Rajdhani
    "12301", "12302",  # Howrah Rajdhani
    "12951", "12957",  # Rajdhanis
    "22435", "22436",  # Vande Bharat
    "22439", "22440",  # Vande Bharat
    "12001", "12002",  # Shatabdi
    "12009", "12010",  # Shatabdi
    "12259", "12260",  # Duronto
)


def guess_is_premium(train_number: str) -> bool:
    if not train_number:
        return False
    return train_number[:5] in {p[:5] for p in PREMIUM_TRAIN_PREFIXES}


async def get(session: AsyncSession, *, train_number: str) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT train_number, train_name, source_station, dest_station,
                   is_premium, route_length_km, avg_cancellation_rate,
                   observation_count
            FROM railpulse.trains
            WHERE train_number = :train_number
            """
        ),
        {"train_number": train_number},
    )
    row = result.first()
    return dict(row._mapping) if row else None


async def get_or_create(
    session: AsyncSession,
    *,
    train_number: str,
    train_name: str | None = None,
    source_station: str | None = None,
    dest_station: str | None = None,
) -> dict[str, Any]:
    """Fetch train row; create a stub with sensible defaults if missing."""
    existing = await get(session, train_number=train_number)
    if existing:
        return existing

    is_premium = guess_is_premium(train_number)
    await session.execute(
        text(
            """
            INSERT INTO railpulse.trains (
                train_number, train_name, source_station, dest_station, is_premium
            ) VALUES (
                :train_number, :train_name, :source_station, :dest_station, :is_premium
            )
            ON CONFLICT (train_number) DO NOTHING
            """
        ),
        {
            "train_number": train_number,
            "train_name": train_name,
            "source_station": source_station,
            "dest_station": dest_station,
            "is_premium": is_premium,
        },
    )
    return {
        "train_number": train_number,
        "train_name": train_name,
        "source_station": source_station,
        "dest_station": dest_station,
        "is_premium": is_premium,
        "route_length_km": None,
        "avg_cancellation_rate": None,
        "observation_count": 0,
    }


async def update_stats(
    session: AsyncSession,
    *,
    train_number: str,
    avg_cancellation_rate: float,
    observation_count: int,
) -> None:
    await session.execute(
        text(
            """
            UPDATE railpulse.trains
            SET avg_cancellation_rate = :rate,
                observation_count = :count,
                updated_at = NOW()
            WHERE train_number = :train_number
            """
        ),
        {
            "train_number": train_number,
            "rate": avg_cancellation_rate,
            "count": observation_count,
        },
    )
