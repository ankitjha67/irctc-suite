"""
GET /v1/model-card — public model card.

Reads the most recent evaluation snapshot from railpulse.model_eval_snapshots.
If no snapshot exists yet (which is the case for v0 since we ship with a
pure heuristic and no eval data), we return an honest fallback that
describes the v0 methodology without fabricating metrics.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ModelCardResponse
from app.config import get_settings
from app.db.connection import get_session
from app.ml.features import FEATURE_VERSION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["model-card"])


V0_METHODOLOGY = (
    "RailPulse v0 ships with a hand-tuned heuristic, not a trained ML model. "
    "The heuristic estimates how far a waitlist is likely to clear by combining "
    "the train's historical cancellation rate (prior: 10%), the number of days "
    "remaining before travel, whether the train is premium (Rajdhani/Shatabdi/"
    "Vande Bharat clear slower), and whether the journey falls in a festive "
    "window (Diwali, Holi, etc.). We compare the user's WL position against "
    "this 'max clearable' estimate to bucket the probability. "
    "Every prediction is logged with its full feature dict so that — once we "
    "observe the actual chart outcome — we can retrain this into a properly "
    "calibrated logistic regression or LightGBM classifier."
)

V0_FEATURES = [
    "is_premium",
    "route_length_km",
    "train_avg_cancellation_rate",
    "train_observation_count",
    "days_before_travel",
    "day_of_week",
    "is_weekend_travel",
    "is_festive_week",
    "is_exam_season",
    "wl_position",
    "wl_position_normalized",
    "wl_position_bucket",
    "ticket_class_one_hot",
    "quota_one_hot",
    "booking_urgency",
]

V0_LIMITATIONS = [
    "v0 is a heuristic — it has no trained parameters and no calibration curve yet.",
    "No data yet on train-specific patterns; every unseen train uses the 10% cancellation prior.",
    "Festive windows are hardcoded for major Indian holidays and may miss regional festivals.",
    "Predictions are probabilistic estimates, not guarantees. Always have a backup plan.",
    "RailPulse does not log into IRCTC and cannot book tickets for you.",
]

DISCLAIMER = (
    "Predictions are probabilistic estimates based on historical patterns and a "
    "simple heuristic. RailPulse is not affiliated with IRCTC and never books "
    "tickets on your behalf. Always have a backup plan for important travel."
)


@router.get("/model-card", response_model=ModelCardResponse)
async def model_card(session: AsyncSession = Depends(get_session)) -> ModelCardResponse:
    settings = get_settings()

    snapshot = await _latest_snapshot(session) if not settings.disable_db else None

    if snapshot is None:
        # Fall back to the static v0 eval JSON file if present, otherwise
        # return the honest "heuristic only" model card.
        file_snapshot = _static_snapshot()
        return ModelCardResponse(
            model_version=settings.model_version,
            methodology=V0_METHODOLOGY + f" Feature schema: {FEATURE_VERSION}.",
            feature_list=V0_FEATURES,
            limitations=V0_LIMITATIONS,
            disclaimer=DISCLAIMER,
            evaluated_at=file_snapshot.get("evaluated_at") if file_snapshot else None,
            sample_size=file_snapshot.get("sample_size") if file_snapshot else None,
            brier_score=file_snapshot.get("brier_score") if file_snapshot else None,
            auc_roc=file_snapshot.get("auc_roc") if file_snapshot else None,
            calibration_curve=file_snapshot.get("calibration_curve") if file_snapshot else None,
        )

    return ModelCardResponse(
        model_version=snapshot["model_version"],
        methodology=V0_METHODOLOGY + f" Feature schema: {FEATURE_VERSION}.",
        feature_list=V0_FEATURES,
        limitations=V0_LIMITATIONS,
        disclaimer=DISCLAIMER,
        evaluated_at=snapshot["evaluated_at"].isoformat() if snapshot.get("evaluated_at") else None,
        sample_size=snapshot.get("sample_size"),
        brier_score=snapshot.get("brier_score"),
        auc_roc=snapshot.get("auc_roc"),
        calibration_curve=snapshot.get("calibration_curve"),
    )


async def _latest_snapshot(session: AsyncSession) -> dict | None:
    try:
        result = await session.execute(
            text(
                """
                SELECT model_version, evaluated_at, sample_size, brier_score,
                       auc_roc, calibration_curve, top_1_accuracy
                FROM railpulse.model_eval_snapshots
                ORDER BY evaluated_at DESC
                LIMIT 1
                """
            )
        )
        row = result.first()
        return dict(row._mapping) if row else None
    except Exception as exc:
        logger.warning("model_eval_snapshots lookup failed: %s", exc)
        return None


def _static_snapshot() -> dict | None:
    """Optional: fall back to a models/v0_eval.json file if train_v0.py wrote one."""
    path = Path("models/v0_eval.json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return {
            "evaluated_at": data.get("trained_at"),
            "sample_size": data.get("test_size"),
            "brier_score": data.get("brier_calibrated") or data.get("brier_score"),
            "auc_roc": data.get("auc_roc"),
            "calibration_curve": data.get("calibration_curve"),
        }
    except Exception:  # pragma: no cover
        return None
