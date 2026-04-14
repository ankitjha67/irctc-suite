"""
Pydantic request/response schemas for the v1 API.
Kept in one place so docs/OpenAPI stay consistent.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


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


class TrackPnrRequest(BaseModel):
    pnr: str = Field(..., min_length=10, max_length=10, pattern="^[0-9]{10}$")


class TrackPnrResponse(BaseModel):
    pnr: str
    train_number: str | None
    travel_date: str | None
    current_status: str
    wl_position: int | None
    chart_prepared: bool
    source: str | None
    destination: str | None
    provider: str


class ModelCardResponse(BaseModel):
    model_version: str
    methodology: str
    feature_list: list[str]
    limitations: list[str]
    disclaimer: str
    evaluated_at: str | None = None
    sample_size: int | None = None
    brier_score: float | None = None
    auc_roc: float | None = None
    calibration_curve: list[dict[str, Any]] | None = None
