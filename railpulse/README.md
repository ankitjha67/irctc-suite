# RailPulse

> Honest PNR confirmation probability for Indian Railways. Calibrated models, public model card, no booking automation.

**What it is:** A waitlist prediction + PNR tracking tool that tells you the probability your WL ticket will confirm, with confidence intervals and a public model card.

**What it is NOT:** A Tatkal booking bot. RailPulse never logs into IRCTC. It reads public data via third-party RapidAPI wrappers and applies ML.

## Stack
- FastAPI (Python 3.12)
- PostgreSQL + TimescaleDB (WL movement time-series)
- LightGBM (v1 model) with isotonic calibration
- Redis (cache + rate limiting)
- Celery (PNR polling, scheduled retraining)
- Next.js frontend (separate repo or `/web` subdir)
- Railway / Fly.io for hosting

## Project layout
```
railpulse/
├── app/
│   ├── main.py                # FastAPI entry
│   ├── config.py               # Settings via pydantic-settings
│   ├── api/
│   │   ├── predict.py          # /predict endpoint
│   │   ├── pnr.py              # /pnr/{pnr} tracking endpoint
│   │   └── health.py
│   ├── ml/
│   │   ├── features.py         # feature engineering
│   │   ├── predict.py          # inference wrapper
│   │   ├── train_v0.py         # cold-start logistic regression
│   │   └── eval.py             # weekly calibration eval
│   ├── data/
│   │   ├── rapidapi_client.py  # IRCTC wrapper adapter (2 providers)
│   │   └── polling.py          # Celery task to poll tracked PNRs
│   └── db/
│       ├── schema.sql
│       └── models.py           # SQLAlchemy models
├── notebooks/
│   └── v0_coldstart.ipynb      # Initial model training
├── tests/
├── pyproject.toml
└── README.md
```

## Setup

```bash
# 1. Python env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Env vars
cp .env.example .env
# Fill RAPIDAPI_KEY, DATABASE_URL, REDIS_URL

# 3. Database
psql $DATABASE_URL -f app/db/schema.sql

# 4. Train the v0 cold-start model (needs Kaggle railway dataset in data/raw/)
python -m app.ml.train_v0

# 5. Run
uvicorn app.main:app --reload
```

## The model card
RailPulse publishes its model card at `/how-predictions-work` including:
- Feature list
- Training data size and date range
- Held-out Brier score and AUC
- Calibration curve (live chart)
- Last retrained timestamp
- Known failure modes

This is a core trust differentiator vs. closed-source competitors.

## Legal posture
- We do not log into IRCTC
- We do not submit booking forms
- We consume public PNR data through RapidAPI's IRCTC wrappers (Railway API, IRCTC1)
- Predictions are probabilistic estimates, not guarantees
- DPDP-compliant: PNR→name mapping retained max 30 days, hashed for analytics
