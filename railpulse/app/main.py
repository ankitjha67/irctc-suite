"""
RailPulse FastAPI application entry.

Exposes:
  POST /v1/predict       — WL→CNF probability for a given query
  POST /v1/pnr/track     — Register a PNR for tracking + get current status
  GET  /v1/pnr/{pnr}     — Get latest status for a tracked PNR
  GET  /v1/model-card    — Public model card data (for /how-predictions-work page)
  GET  /health
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import get_settings
from app.data.rapidapi_client import PnrClient
from app.ml.features import QueryContext, TrainMetadata
from app.ml.predict import get_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm-load the model on startup so first prediction isn't slow
    get_model()
    logger.info("RailPulse started — env=%s model=%s", settings.env, settings.model_version)
    yield
    logger.info("RailPulse shutting down")


app = FastAPI(
    title="RailPulse API",
    version=settings.model_version,
    description="Honest PNR confirmation probability. Not affiliated with IRCTC.",
    lifespan=lifespan,
)

# CORS — tighten in prod to your own domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "dev" else ["https://railpulse.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

pnr_client = PnrClient()


# ─── Request / response models ───────────────────────────────────────────────

class PredictRequest(BaseModel):
    train_number: str = Field(..., min_length=4, max_length=6)
    travel_date: date
    source_station: str = Field(..., min_length=3, max_length=5)
    dest_station: str = Field(..., min_length=3, max_length=5)
    ticket_class: str = Field(..., pattern="^(SL|3A|2A|1A|CC|EC)$")
    quota: str = Field("GN", pattern="^(GN|TQ|LD|PT)$")
    current_wl_position: int = Field(..., ge=1, le=500)


class PredictResponse(BaseModel):
    probability: float
    bucket: str
    confidence_lo: float
    confidence_hi: float
    model_version: str
    warnings: list[str]
    # We deliberately do NOT return the full feature dict to the public —
    # that's reserved for the model card page


class TrackPnrRequest(BaseModel):
    pnr: str = Field(..., min_length=10, max_length=10, pattern="^[0-9]{10}$")


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.model_version,
        "env": settings.env,
    }


@app.post("/v1/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request) -> PredictResponse:
    # TODO (Weekend 3): rate limit via Redis, check user tier from JWT
    # TODO (Weekend 2): look up train metadata from DB instead of stub defaults

    ctx = QueryContext(
        train_number=req.train_number,
        travel_date=req.travel_date,
        source_station=req.source_station.upper(),
        dest_station=req.dest_station.upper(),
        ticket_class=req.ticket_class,
        quota=req.quota,
        current_wl_position=req.current_wl_position,
    )

    # Stub train metadata for now — replace with DB lookup
    train = TrainMetadata(
        train_name="Unknown",
        is_premium=_guess_premium(req.train_number),
        route_length_km=None,
        avg_cancellation_rate=0.10,  # prior; refined as we collect data
        observation_count=0,
    )

    model = get_model()
    result = model.predict(ctx, train)

    # TODO (Weekend 2): log this prediction to `predictions` table for future eval

    return PredictResponse(
        probability=result.probability,
        bucket=result.bucket,
        confidence_lo=result.confidence_lo,
        confidence_hi=result.confidence_hi,
        model_version=result.model_version,
        warnings=result.warnings,
    )


@app.post("/v1/pnr/track")
async def track_pnr(req: TrackPnrRequest) -> dict[str, Any]:
    try:
        status = await pnr_client.fetch(req.pnr)
    except Exception as e:
        logger.error("PNR fetch failed for %s: %s", req.pnr, e)
        raise HTTPException(status_code=502, detail="Unable to fetch PNR status right now")

    # TODO (Weekend 2):
    #  - upsert to `pnrs` table
    #  - write to pnr_status_history hypertable
    #  - if user authenticated, associate with user_id

    return {
        "pnr": status.pnr,
        "train_number": status.train_number,
        "travel_date": status.travel_date,
        "current_status": status.current_status,
        "wl_position": status.wl_position,
        "chart_prepared": status.chart_prepared,
        "source": status.source,
        "destination": status.destination,
        "provider": status.provider,
    }


@app.get("/v1/model-card")
async def model_card() -> dict[str, Any]:
    """
    Public model card for /how-predictions-work page.

    In production this reads from model_eval_snapshots table; for now it reads
    the v0 eval JSON file produced by train_v0.py.
    """
    import json
    from pathlib import Path

    eval_path = Path("models/v0_eval.json")
    if not eval_path.exists():
        return {
            "status": "no_eval_available",
            "message": "Model has not been evaluated yet. Train the v0 model first.",
        }

    data = json.loads(eval_path.read_text())
    return {
        "model_version": data["model_version"],
        "trained_at": data["trained_at"],
        "training_size": data["training_size"],
        "test_size": data["test_size"],
        "brier_score": data["brier_calibrated"],
        "auc_roc": data["auc_roc"],
        "calibration_curve": data["calibration_curve"],
        "feature_count": len(data["feature_columns"]),
        "disclaimer": (
            "Predictions are probabilistic estimates based on historical patterns. "
            "We make no guarantee of confirmation. Always have a backup plan."
        ),
    }


def _guess_premium(train_number: str) -> bool:
    """Rough heuristic until we seed the trains table. Rajdhanis start with 12, Vande Bharats with 22."""
    return train_number.startswith(("12951", "12952", "12953", "12954", "22435", "22436"))
