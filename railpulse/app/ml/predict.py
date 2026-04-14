"""
Prediction wrapper.

Loads the serialized model + calibrator at startup and provides a single `predict`
function that returns a calibrated probability, bucket, and confidence interval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.config import get_settings
from app.ml.features import (
    QueryContext,
    TrainMetadata,
    compute_features,
    features_to_model_input,
)

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    probability: float          # calibrated, 0–1
    bucket: str                 # 'high' / 'medium' / 'low'
    confidence_lo: float        # 10th percentile estimate
    confidence_hi: float        # 90th percentile estimate
    model_version: str
    features_used: dict[str, Any]
    warnings: list[str]


class RailPulseModel:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model: Any = None
        self.calibrator: Any = None
        self.feature_columns: list[str] = []
        self.loaded = False

    def load(self) -> None:
        path = Path(self.settings.model_path)
        if not path.exists():
            logger.warning("Model file not found at %s — predictions will use fallback", path)
            return

        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.calibrator = bundle.get("calibrator")
        self.feature_columns = bundle["feature_columns"]
        self.loaded = True
        logger.info(
            "Loaded model version=%s features=%d calibrated=%s",
            bundle.get("version", "unknown"),
            len(self.feature_columns),
            self.calibrator is not None,
        )

    def predict(self, ctx: QueryContext, train: TrainMetadata) -> PredictionResult:
        warnings: list[str] = []
        features = compute_features(ctx, train)
        numeric = features_to_model_input(features)

        if not self.loaded:
            # Fallback heuristic for cold-start / model-load failures.
            # Based on common patterns: position normalized by capacity, decayed by days_before.
            prob = self._fallback_heuristic(features)
            warnings.append("Model not loaded — using fallback heuristic. Trust these predictions less.")
        else:
            x = np.array([[numeric.get(c, 0.0) for c in self.feature_columns]])
            raw_prob = float(self.model.predict_proba(x)[0, 1])
            prob = (
                float(self.calibrator.predict([raw_prob])[0])
                if self.calibrator is not None
                else raw_prob
            )

        # Confidence interval: bootstrap over feature perturbation in v1,
        # for v0 we approximate with a fixed ± based on training observation count.
        obs_count = train.observation_count
        if obs_count < 100:
            warnings.append(
                f"Only {obs_count} historical observations for this train — predictions are less reliable."
            )
            band = 0.20
        elif obs_count < 1000:
            band = 0.12
        else:
            band = 0.08

        lo = max(0.0, prob - band)
        hi = min(1.0, prob + band)

        bucket = "high" if prob >= 0.70 else "medium" if prob >= 0.35 else "low"

        return PredictionResult(
            probability=round(prob, 3),
            bucket=bucket,
            confidence_lo=round(lo, 3),
            confidence_hi=round(hi, 3),
            model_version=self.settings.model_version,
            features_used=features,
            warnings=warnings,
        )

    @staticmethod
    def _fallback_heuristic(features: dict[str, Any]) -> float:
        """
        Zero-model fallback. DO NOT ship this as the primary predictor.
        Calibrated on rough intuitions from published Confirmtkt/ixigo stats.
        """
        days = features["days_before_travel"]
        premium = features["is_premium"]
        festive = features["is_festive_week"]
        cancel_rate = features["train_avg_cancellation_rate"]

        # Start from train's own cancellation rate × days before → max WL that usually clears
        max_clearable = cancel_rate * days * (1.5 if not premium else 0.8) * 100
        if festive:
            max_clearable *= 0.6

        wl_pos = features["wl_position"]
        if wl_pos <= max_clearable * 0.4:
            return 0.85
        if wl_pos <= max_clearable * 0.8:
            return 0.55
        if wl_pos <= max_clearable * 1.2:
            return 0.30
        return 0.10


# Module-level singleton
_model_instance: RailPulseModel | None = None


def get_model() -> RailPulseModel:
    global _model_instance
    if _model_instance is None:
        _model_instance = RailPulseModel()
        _model_instance.load()
    return _model_instance
