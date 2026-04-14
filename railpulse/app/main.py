"""
RailPulse FastAPI application entry.

Exposes (all versioned under /v1):
  POST /v1/predict       — WL→CNF probability for a given query
  POST /v1/pnr/track     — Fetch current PNR status, persist it for eval
  GET  /v1/pnr/{pnr}     — Latest known status + history for a tracked PNR
  GET  /v1/model-card    — Public model card (methodology + eval metrics)
  GET  /health           — Liveness probe
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.model_card import router as model_card_router
from app.api.pnr import router as pnr_router
from app.api.predict import router as predict_router
from app.config import get_settings
from app.ml.predict import get_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Warm-load the model so the first prediction isn't slow. In v0 this is
    # the heuristic; Weekend 2 will swap in a real trained model.
    get_model()
    logger.info(
        "RailPulse started — env=%s model=%s",
        settings.env,
        settings.model_version,
    )
    yield
    logger.info("RailPulse shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RailPulse API",
        version=settings.model_version,
        description=(
            "Honest PNR confirmation probability for Indian Railways. "
            "Not affiliated with IRCTC. Read-only intelligence layer — "
            "RailPulse never books tickets on your behalf."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.env == "dev" else ["https://railpulse.app"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(predict_router)
    app.include_router(pnr_router)
    app.include_router(model_card_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": settings.model_version,
            "env": settings.env,
        }

    return app


app = create_app()
