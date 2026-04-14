"""
PNRs repository — tracked PNRs + poll history.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_pnr(
    session: AsyncSession,
    *,
    pnr: str,
    train_number: str | None,
    travel_date: date | None,
    source: str | None,
    destination: str | None,
    ticket_class: str | None,
    quota: str | None,
    owner_user_id: UUID | None = None,
) -> None:
    """Insert a new tracked PNR or refresh its metadata if already tracked."""
    await session.execute(
        text(
            """
            INSERT INTO railpulse.pnrs (
                pnr, train_number, travel_date, source, destination,
                class, quota, owner_user_id, last_polled_at, poll_count
            ) VALUES (
                :pnr, :train_number, :travel_date, :source, :destination,
                :class, :quota, :owner_user_id, :now, 1
            )
            ON CONFLICT (pnr) DO UPDATE SET
                train_number = COALESCE(EXCLUDED.train_number, railpulse.pnrs.train_number),
                travel_date = COALESCE(EXCLUDED.travel_date, railpulse.pnrs.travel_date),
                source = COALESCE(EXCLUDED.source, railpulse.pnrs.source),
                destination = COALESCE(EXCLUDED.destination, railpulse.pnrs.destination),
                class = COALESCE(EXCLUDED.class, railpulse.pnrs.class),
                quota = COALESCE(EXCLUDED.quota, railpulse.pnrs.quota),
                owner_user_id = COALESCE(EXCLUDED.owner_user_id, railpulse.pnrs.owner_user_id),
                last_polled_at = EXCLUDED.last_polled_at,
                poll_count = railpulse.pnrs.poll_count + 1
            """
        ),
        {
            "pnr": pnr,
            "train_number": train_number,
            "travel_date": _coerce_date(travel_date),
            "source": source,
            "destination": destination,
            "class": ticket_class,
            "quota": quota,
            "owner_user_id": str(owner_user_id) if owner_user_id else None,
            "now": datetime.utcnow(),
        },
    )


async def record_status(
    session: AsyncSession,
    *,
    pnr: str,
    wl_position: int | None,
    status_code: str,
    status_text: str | None,
    raw_response: dict[str, Any] | None,
) -> None:
    """Append a row to railpulse.pnr_status_history for this poll."""
    await session.execute(
        text(
            """
            INSERT INTO railpulse.pnr_status_history (
                pnr, observed_at, wl_position, status_code, status_text, raw_response
            ) VALUES (
                :pnr, :observed_at, :wl_position, :status_code, :status_text,
                CAST(:raw_response AS JSONB)
            )
            """
        ),
        {
            "pnr": pnr,
            "observed_at": datetime.utcnow(),
            "wl_position": wl_position,
            "status_code": status_code,
            "status_text": status_text,
            "raw_response": json.dumps(raw_response) if raw_response is not None else None,
        },
    )


async def mark_chart_prepared(session: AsyncSession, *, pnr: str, final_status: str) -> None:
    await session.execute(
        text(
            """
            UPDATE railpulse.pnrs
            SET chart_prepared_at = :now, final_status = :final_status
            WHERE pnr = :pnr AND chart_prepared_at IS NULL
            """
        ),
        {"pnr": pnr, "now": datetime.utcnow(), "final_status": final_status},
    )


async def find_due_for_polling(
    session: AsyncSession, *, limit: int = 20
) -> list[dict[str, Any]]:
    """PNRs whose chart hasn't been prepared yet and haven't been polled recently."""
    result = await session.execute(
        text(
            """
            SELECT pnr, train_number, travel_date, last_polled_at
            FROM railpulse.pnrs
            WHERE chart_prepared_at IS NULL
              AND travel_date >= CURRENT_DATE
            ORDER BY last_polled_at NULLS FIRST
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in result]


async def count_tracked_for_subject(
    session: AsyncSession, *, subject_key: str
) -> int:
    """Count how many future PNRs this subject currently has tracked."""
    # v0 uses api_usage.tracked_pnr_count for the daily cap, but this function
    # is what the /v1/pnr/track handler uses to decide whether to accept a new
    # tracking request. For v0 we count the pnrs owned by this subject that
    # haven't had their chart prepared yet.
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM railpulse.pnrs
            WHERE owner_user_id::TEXT = :subject_key
              AND chart_prepared_at IS NULL
            """
        ),
        {"subject_key": subject_key},
    )
    return int(result.scalar() or 0)


def _coerce_date(value: Any) -> date | None:
    if value is None or isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None
