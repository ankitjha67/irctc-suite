"""Prediction wrapper tests — covers the fallback heuristic path used in v0."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.ml.features import QueryContext, TrainMetadata
from app.ml.predict import RailPulseModel


@pytest.fixture
def model() -> RailPulseModel:
    m = RailPulseModel()
    # Force fallback heuristic regardless of whether a model file exists locally.
    m.loaded = False
    return m


def _ctx(**overrides) -> QueryContext:
    defaults = dict(
        train_number="12951",
        travel_date=date.today() + timedelta(days=14),
        source_station="BCT",
        dest_station="NDLS",
        ticket_class="3A",
        quota="GN",
        current_wl_position=10,
    )
    defaults.update(overrides)
    return QueryContext(**defaults)


def _train(**overrides) -> TrainMetadata:
    defaults = dict(
        train_name="Test",
        is_premium=False,
        route_length_km=1000,
        avg_cancellation_rate=0.12,
        observation_count=500,
    )
    defaults.update(overrides)
    return TrainMetadata(**defaults)


def test_probability_in_unit_interval(model):
    result = model.predict(_ctx(), _train())
    assert 0.0 <= result.probability <= 1.0


def test_confidence_interval_brackets_probability(model):
    result = model.predict(_ctx(), _train())
    assert 0.0 <= result.confidence_lo <= result.probability <= result.confidence_hi <= 1.0


def test_bucket_matches_probability(model):
    result = model.predict(_ctx(current_wl_position=2), _train(observation_count=2000))
    assert result.bucket in {"high", "medium", "low"}


def test_low_wl_position_yields_higher_probability_than_high(model):
    low = model.predict(_ctx(current_wl_position=3), _train())
    high = model.predict(_ctx(current_wl_position=150), _train())
    assert low.probability >= high.probability


def test_unloaded_model_emits_warning(model):
    result = model.predict(_ctx(), _train())
    assert any("fallback" in w.lower() for w in result.warnings)


def test_low_observation_count_widens_confidence_band(model):
    low_obs = model.predict(_ctx(), _train(observation_count=10))
    high_obs = model.predict(_ctx(), _train(observation_count=5000))
    low_band = low_obs.confidence_hi - low_obs.confidence_lo
    high_band = high_obs.confidence_hi - high_obs.confidence_lo
    assert low_band >= high_band


def test_model_version_propagated(model):
    result = model.predict(_ctx(), _train())
    assert result.model_version  # non-empty


def test_features_used_attached(model):
    result = model.predict(_ctx(), _train())
    assert "wl_position" in result.features_used
    assert result.features_used["wl_position"] == 10
