"""
POST /v1/predict — WL→CNF confirmation probability.

Flow:
  1. Rate-limit dependency increments the per-subject counter; raises 429 if over.
  2. Look up / lazy-create the train reference row so the heuristic has good priors.
  3. Run the prediction model (heuristic in v0).
  4. Log the prediction (with full feature dict) for future eval.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rate_limit import enforce_prediction_rate_limit
from app.api.schemas import PredictRequest, PredictResponse
from app.config import get_settings
from app.db.connection import get_session
from app.db.repositories import predictions as predictions_repo
from app.db.repositories import trains as trains_repo
from app.ml.features import QueryContext, TrainMetadata
from app.ml.predict import get_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
async def predict(
    req: PredictRequest,
    subject_key: str = Depends(enforce_prediction_rate_limit),
    session: AsyncSession = Depends(get_session),
) -> PredictResponse:
    settings = get_settings()

    ctx = QueryContext(
        train_number=req.train_number,
        travel_date=req.travel_date,
        source_station=req.source_station.upper(),
        dest_station=req.dest_station.upper(),
        ticket_class=req.ticket_class,
        quota=req.quota,
        current_wl_position=req.current_wl_position,
    )

    train_row = await _resolve_train(session, req.train_number)
    train = TrainMetadata(
        train_name=train_row.get("train_name") or "Unknown",
        is_premium=bool(train_row.get("is_premium")),
        route_length_km=train_row.get("route_length_km"),
        avg_cancellation_rate=train_row.get("avg_cancellation_rate") or 0.10,
        observation_count=int(train_row.get("observation_count") or 0),
    )

    model = get_model()
    result = model.predict(ctx, train)

    # Log every prediction with its full feature dict for later eval/training.
    if not settings.disable_db:
        try:
            await predictions_repo.log_prediction(
                session,
                features=result.features_used,
                predicted_prob=result.probability,
                predicted_bucket=result.bucket,
                confidence_lo=result.confidence_lo,
                confidence_hi=result.confidence_hi,
                model_version=result.model_version,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to log prediction: %s", exc)

    return PredictResponse(
        probability=result.probability,
        bucket=result.bucket,
        confidence_lo=result.confidence_lo,
        confidence_hi=result.confidence_hi,
        model_version=result.model_version,
        warnings=result.warnings,
    )


async def _resolve_train(session: AsyncSession, train_number: str) -> dict:
    """Look up train row from the reference table; fall back to a stub if DB is off."""
    settings = get_settings()
    if settings.disable_db:
        return {
            "train_name": None,
            "is_premium": trains_repo.guess_is_premium(train_number),
            "route_length_km": None,
            "avg_cancellation_rate": None,
            "observation_count": 0,
        }
    return await trains_repo.get_or_create(session, train_number=train_number)
