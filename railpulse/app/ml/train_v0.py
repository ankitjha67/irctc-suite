"""
v0 cold-start training — logistic regression with hand-crafted features and
isotonic calibration.

Data expectations:
  - data/raw/pnr_outcomes.csv
    Columns: train_number, travel_date, source, destination, class, quota,
             initial_wl_position, days_before_booking, final_status
  - Final status mapped to binary: CNF or RAC → 1; CAN or WL-at-chart → 0

This is intended as a bootstrap model. Replace with LightGBM once you have
≥1000 real observations logged from production.

Run:
    python -m app.ml.train_v0
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from app.ml.features import (
    FEATURE_VERSION,
    QueryContext,
    TrainMetadata,
    compute_features,
    features_to_model_input,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = Path("data/raw/pnr_outcomes.csv")
MODEL_OUT = Path("models/v0_logistic.pkl")
EVAL_OUT = Path("models/v0_eval.json")


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Expected {DATA_PATH}. Download a Kaggle Indian Railways PNR dataset "
            f"or bootstrap with synthetic data from data/synthetic.py."
        )
    df = pd.read_csv(DATA_PATH, parse_dates=["travel_date"])
    logger.info("Loaded %d rows from %s", len(df), DATA_PATH)
    return df


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list[str]]:
    """Apply the exact same feature engineering used at inference time."""
    rows: list[dict[str, float]] = []
    for _, r in df.iterrows():
        ctx = QueryContext(
            train_number=r["train_number"],
            travel_date=r["travel_date"].date(),
            source_station=r["source"],
            dest_station=r["destination"],
            ticket_class=r["class"],
            quota=r.get("quota", "GN"),
            current_wl_position=int(r["initial_wl_position"]),
            booking_datetime=(
                r["travel_date"] - pd.Timedelta(days=int(r.get("days_before_booking", 30)))
            ).to_pydatetime() if not pd.isna(r.get("days_before_booking")) else None,
        )
        train = TrainMetadata(
            train_name=r.get("train_name", "Unknown"),
            is_premium=bool(r.get("is_premium", False)),
            route_length_km=int(r.get("route_length_km", 0)) or None,
            avg_cancellation_rate=float(r.get("avg_cancellation_rate", 0.10)),
            observation_count=int(r.get("observation_count", 100)),
        )
        features = compute_features(ctx, train)
        rows.append(features_to_model_input(features))

    X = pd.DataFrame(rows).fillna(0.0)
    # Label: CNF or RAC → 1, everything else → 0
    y = df["final_status"].isin(["CNF", "RAC"]).astype(int).to_numpy()
    columns = sorted(X.columns.tolist())
    X = X[columns]
    return X, y, columns


def train():
    df = load_data()
    X, y, feature_columns = build_feature_matrix(df)
    logger.info("Feature matrix: %s, positive rate: %.3f", X.shape, y.mean())

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    # Further split train → train + calibration
    X_tr, X_cal, y_tr, y_cal = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )

    # Base model: logistic regression with scaling
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=500, C=1.0, class_weight="balanced")),
    ])
    model.fit(X_tr, y_tr)

    # Isotonic calibration on held-out calibration set
    cal_raw = model.predict_proba(X_cal)[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(cal_raw, y_cal)

    # Evaluate on test set
    test_raw = model.predict_proba(X_test)[:, 1]
    test_cal = calibrator.predict(test_raw)

    brier_raw = brier_score_loss(y_test, test_raw)
    brier_cal = brier_score_loss(y_test, test_cal)
    auc = roc_auc_score(y_test, test_cal)

    logger.info("Brier (raw):        %.4f", brier_raw)
    logger.info("Brier (calibrated): %.4f", brier_cal)
    logger.info("AUC-ROC:            %.4f", auc)

    # Calibration curve (10 buckets)
    curve = calibration_curve(y_test, test_cal, n_bins=10)

    # Save bundle
    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "calibrator": calibrator,
            "feature_columns": feature_columns,
            "feature_version": FEATURE_VERSION,
            "version": "v0.1.0",
            "trained_at": datetime.utcnow().isoformat(),
            "training_size": len(X_tr),
        },
        MODEL_OUT,
    )

    # Save eval snapshot for the public model card
    eval_data = {
        "model_version": "v0.1.0",
        "trained_at": datetime.utcnow().isoformat(),
        "training_size": len(X_tr),
        "test_size": len(X_test),
        "brier_raw": round(brier_raw, 4),
        "brier_calibrated": round(brier_cal, 4),
        "auc_roc": round(auc, 4),
        "calibration_curve": curve,
        "feature_columns": feature_columns,
    }
    EVAL_OUT.write_text(json.dumps(eval_data, indent=2))
    logger.info("Saved model to %s and eval to %s", MODEL_OUT, EVAL_OUT)


def calibration_curve(y_true, y_prob, n_bins=10):
    """Return a list of {predicted_mean, actual_rate, count} per bin."""
    bins = np.linspace(0, 1, n_bins + 1)
    out = []
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1] if i < n_bins - 1 else y_prob <= bins[i + 1])
        if mask.sum() == 0:
            continue
        out.append({
            "bin_lo": round(float(bins[i]), 2),
            "bin_hi": round(float(bins[i + 1]), 2),
            "predicted_mean": round(float(y_prob[mask].mean()), 3),
            "actual_rate": round(float(y_true[mask].mean()), 3),
            "count": int(mask.sum()),
        })
    return out


if __name__ == "__main__":
    train()
