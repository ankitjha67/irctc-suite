"""Feature engineering tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.ml.features import (
    FEATURE_VERSION,
    QueryContext,
    TrainMetadata,
    compute_features,
    features_to_model_input,
)


def _ctx(**overrides):
    defaults = dict(
        train_number="12951",
        travel_date=date.today() + timedelta(days=14),
        source_station="BCT",
        dest_station="NDLS",
        ticket_class="3A",
        quota="GN",
        current_wl_position=10,
        booking_datetime=datetime.now(),
    )
    defaults.update(overrides)
    return QueryContext(**defaults)


def _train(**overrides):
    defaults = dict(
        train_name="Mumbai Rajdhani",
        is_premium=True,
        route_length_km=1384,
        avg_cancellation_rate=0.12,
        observation_count=500,
    )
    defaults.update(overrides)
    return TrainMetadata(**defaults)


def test_feature_version_is_stamped():
    f = compute_features(_ctx(), _train())
    assert f["feature_version"] == FEATURE_VERSION


def test_days_before_travel_positive():
    ctx = _ctx(travel_date=date.today() + timedelta(days=30))
    f = compute_features(ctx, _train())
    # Should be ~30 days, allow ±1 to cover midnight boundary.
    assert 29 <= f["days_before_travel"] <= 30


def test_days_before_travel_clamps_to_zero_for_past_dates():
    ctx = _ctx(travel_date=date.today() - timedelta(days=5))
    f = compute_features(ctx, _train())
    assert f["days_before_travel"] == 0


def test_extreme_wl_position_bucket():
    f = compute_features(_ctx(current_wl_position=150), _train())
    assert f["wl_position_bucket"] == "very_high"
    # Normalized against a 3A coach capacity of 64, WL 150 should be >2.0
    assert f["wl_position_normalized"] > 2.0


def test_very_low_wl_bucket():
    f = compute_features(_ctx(current_wl_position=3), _train())
    assert f["wl_position_bucket"] == "very_low"


def test_festive_week_detection_diwali():
    # 25 Oct is inside the (10, 20, 31) festive window
    ctx = _ctx(travel_date=date(date.today().year + 1, 10, 25))
    f = compute_features(ctx, _train())
    assert f["is_festive_week"] == 1
    assert f["festive_name"] == "diwali"


def test_non_festive_week():
    ctx = _ctx(travel_date=date(date.today().year + 1, 6, 15))
    f = compute_features(ctx, _train())
    assert f["is_festive_week"] == 0


def test_class_one_hot_exclusive():
    f = compute_features(_ctx(ticket_class="SL"), _train())
    one_hots = [f[k] for k in ["class_SL", "class_3A", "class_2A", "class_1A", "class_CC", "class_EC"]]
    assert sum(one_hots) == 1
    assert f["class_SL"] == 1


def test_premium_flag_propagated_from_train_metadata():
    f_premium = compute_features(_ctx(), _train(is_premium=True))
    f_normal = compute_features(_ctx(), _train(is_premium=False))
    assert f_premium["is_premium"] == 1
    assert f_normal["is_premium"] == 0


def test_features_to_model_input_drops_non_numeric():
    f = compute_features(_ctx(), _train())
    numeric = features_to_model_input(f)
    assert "festive_name" not in numeric
    assert "wl_position_bucket" not in numeric
    assert "booking_urgency" not in numeric
    assert "feature_version" not in numeric
    # Everything that remains should be a float.
    for v in numeric.values():
        assert isinstance(v, float)


@pytest.mark.parametrize(
    "days,expected",
    [
        (0, "tatkal_window"),
        (1, "tatkal_window"),
        (5, "last_week"),
        (20, "normal"),
        (60, "advance"),
    ],
)
def test_booking_urgency_buckets(days, expected):
    ctx = _ctx(travel_date=date.today() + timedelta(days=days))
    f = compute_features(ctx, _train())
    assert f["booking_urgency"] == expected
