"""
Feature engineering for WL→CNF prediction.

Design notes:
- All features are computed from: train metadata, query-time context, and historical
  WL movement (if available). No IRCTC-credential-based features.
- Features are versioned; when we change the schema we bump FEATURE_VERSION and retrain.
- The same `compute_features` function is used at training time AND inference time to
  prevent train/serve skew.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Any

FEATURE_VERSION = "v1"

# Known premium train prefixes (Rajdhani, Shatabdi, Vande Bharat, Duronto, Tejas)
PREMIUM_PATTERNS = {
    "rajdhani", "shatabdi", "vande bharat", "duronto", "tejas", "humsafar", "gatimaan"
}

# Festive windows (hardcoded for India; refine with historical data)
FESTIVE_WINDOWS = [
    # (month, start_day, end_day, name)
    (10, 20, 31, "diwali"),
    (11, 1, 10, "diwali"),
    (12, 20, 31, "xmas_ny"),
    (1, 1, 5, "xmas_ny"),
    (3, 1, 15, "holi"),
    (8, 10, 20, "independence"),
]

EXAM_SEASON_MONTHS = {3, 4, 5}  # board exams + entrance tests


@dataclass
class QueryContext:
    """Inputs the user provides at prediction time."""
    train_number: str
    travel_date: date
    source_station: str
    dest_station: str
    ticket_class: str            # SL / 3A / 2A / 1A / CC / EC
    quota: str                    # GN / TQ / LD / PT
    current_wl_position: int
    booking_datetime: datetime | None = None  # when they booked, for "days before travel"


@dataclass
class TrainMetadata:
    """Pulled from trains table at prediction time."""
    train_name: str
    is_premium: bool
    route_length_km: int | None
    avg_cancellation_rate: float | None   # rolling 90d, 0–1
    observation_count: int                 # how much data we have on this train


def _days_before_travel(ctx: QueryContext) -> int:
    booking = ctx.booking_datetime or datetime.now()
    delta = (ctx.travel_date - booking.date()).days
    return max(delta, 0)


def _is_festive_week(d: date) -> tuple[bool, str]:
    for month, start_day, end_day, name in FESTIVE_WINDOWS:
        if d.month == month and start_day <= d.day <= end_day:
            return True, name
    return False, "none"


def _class_capacity(ticket_class: str) -> int:
    """Rough typical coach capacity per class. Used for position normalization."""
    return {
        "SL": 72,
        "3A": 64,
        "2A": 46,
        "1A": 18,
        "CC": 78,
        "EC": 56,
    }.get(ticket_class.upper(), 64)


def compute_features(ctx: QueryContext, train: TrainMetadata) -> dict[str, Any]:
    """
    Produce the feature dict used by the model.

    CRITICAL: Any change here must be reflected in the training pipeline AND the model
    file must be retrained. Never silently add/remove features from a deployed model.
    """
    days_before = _days_before_travel(ctx)
    festive, festive_name = _is_festive_week(ctx.travel_date)
    capacity = _class_capacity(ctx.ticket_class)

    features: dict[str, Any] = {
        "feature_version": FEATURE_VERSION,

        # Train-level
        "is_premium": int(train.is_premium),
        "route_length_km": train.route_length_km or 0,
        "train_avg_cancellation_rate": train.avg_cancellation_rate or 0.10,  # prior
        "train_observation_count": train.observation_count,

        # Temporal
        "days_before_travel": days_before,
        "day_of_week": ctx.travel_date.weekday(),
        "is_weekend_travel": int(ctx.travel_date.weekday() >= 5),
        "is_festive_week": int(festive),
        "festive_name": festive_name,
        "is_exam_season": int(ctx.travel_date.month in EXAM_SEASON_MONTHS),

        # Position
        "wl_position": ctx.current_wl_position,
        "wl_position_normalized": ctx.current_wl_position / max(capacity, 1),
        "wl_position_bucket": _bucket_wl(ctx.current_wl_position),

        # Class / quota
        "class_SL": int(ctx.ticket_class.upper() == "SL"),
        "class_3A": int(ctx.ticket_class.upper() == "3A"),
        "class_2A": int(ctx.ticket_class.upper() == "2A"),
        "class_1A": int(ctx.ticket_class.upper() == "1A"),
        "class_CC": int(ctx.ticket_class.upper() == "CC"),
        "class_EC": int(ctx.ticket_class.upper() == "EC"),
        "quota_GN": int(ctx.quota.upper() == "GN"),
        "quota_TQ": int(ctx.quota.upper() == "TQ"),
        "quota_LD": int(ctx.quota.upper() == "LD"),
        "capacity_for_class": capacity,

        # Derived
        "booking_urgency": _booking_urgency(days_before),
    }

    return features


def _bucket_wl(wl: int) -> str:
    if wl <= 5:
        return "very_low"
    if wl <= 15:
        return "low"
    if wl <= 40:
        return "medium"
    if wl <= 80:
        return "high"
    return "very_high"


def _booking_urgency(days_before: int) -> str:
    if days_before <= 1:
        return "tatkal_window"
    if days_before <= 7:
        return "last_week"
    if days_before <= 30:
        return "normal"
    return "advance"


def features_to_model_input(features: dict[str, Any]) -> dict[str, float]:
    """
    Convert the human-readable feature dict into the numeric vector the model expects.

    Any non-numeric features (festive_name, wl_position_bucket, booking_urgency) are
    dropped here — v0 logistic regression doesn't use them. v1+ LightGBM will one-hot
    or target-encode them.
    """
    drop = {"feature_version", "festive_name", "wl_position_bucket", "booking_urgency"}
    return {k: float(v) for k, v in features.items() if k not in drop and not isinstance(v, str)}
