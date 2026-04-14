"""
Predictions repository.

Every call to POST /v1/predict writes a row here with the full feature dict
so that — once we observe the actual outcome for the matching PNR — we can
backfill ``actual_outcome`` and build a labeled training set.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_prediction(
    session: AsyncSession,
    *,
    features: dict[str, Any],
    predicted_prob: float,
    predicted_bucket: str,
    confidence_lo: float,
    confidence_hi: float,
    model_version: str,
    pnr: str | None = None,
    user_id: UUID | None = None,
) -> UUID:
    """Insert a row and return its id."""
    pid = uuid4()
    await session.execute(
        text(
            """
            INSERT INTO railpulse.predictions (
                id, pnr, user_id, features, predicted_prob, predicted_bucket,
                confidence_lo, confidence_hi, model_version
            ) VALUES (
                :id, :pnr, :user_id, CAST(:features AS JSONB), :predicted_prob,
                :predicted_bucket, :confidence_lo, :confidence_hi, :model_version
            )
            """
        ),
        {
            "id": str(pid),
            "pnr": pnr,
            "user_id": str(user_id) if user_id else None,
            "features": json.dumps(_json_safe(features)),
            "predicted_prob": predicted_prob,
            "predicted_bucket": predicted_bucket,
            "confidence_lo": confidence_lo,
            "confidence_hi": confidence_hi,
            "model_version": model_version,
        },
    )
    return pid


async def find_pending_eval(
    session: AsyncSession, *, limit: int = 100
) -> list[dict[str, Any]]:
    """Return predictions that don't yet have an actual_outcome."""
    result = await session.execute(
        text(
            """
            SELECT id, pnr, features, predicted_prob, predicted_bucket, made_at
            FROM railpulse.predictions
            WHERE actual_outcome IS NULL
            ORDER BY made_at ASC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in result]


async def update_outcome(
    session: AsyncSession,
    *,
    prediction_id: UUID,
    actual_outcome: str,
) -> None:
    """Fill in actual_outcome once chart prep has happened."""
    await session.execute(
        text(
            """
            UPDATE railpulse.predictions
            SET actual_outcome = :actual_outcome,
                scored_at = :scored_at
            WHERE id = :id
            """
        ),
        {
            "id": str(prediction_id),
            "actual_outcome": actual_outcome,
            "scored_at": datetime.utcnow(),
        },
    )


def _json_safe(value: Any) -> Any:
    """Convert non-JSON-serializable feature values (dates, etc.) to strings."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, int | float | bool | str) or value is None:
        return value
    return str(value)
