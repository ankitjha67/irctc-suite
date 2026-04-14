# RailPulse

> Honest PNR confirmation probability for Indian Railways. Public model card, no booking automation.

**What it is:** A waitlist prediction + PNR tracking API that tells you the probability your WL ticket will confirm, with confidence intervals and a public model card.

**What it is NOT:** A Tatkal booking bot. RailPulse never logs into IRCTC. It reads public data via third-party RapidAPI wrappers and applies a prediction model on top.

## v0 scope (shipping now)

- **API-only, no frontend.** Three endpoints under `/v1/`:
  - `POST /v1/predict` — probability that a given WL ticket will confirm
  - `POST /v1/pnr/track` — fetch live PNR status and persist it for future eval
  - `GET /v1/pnr/{pnr}` — latest known status + poll history for a tracked PNR
  - `GET /v1/model-card` — public methodology and (once we have data) live eval metrics
- **v0 is a heuristic, not a trained model.** The `/v1/model-card` endpoint
  says so honestly. Every prediction is logged with its full feature dict so
  that once we observe enough real chart outcomes we can retrain the
  predictor without changing the API shape.
- **Rate limits are app-level** (5 predictions / 2 tracked PNRs per IP per day
  on the free tier). Enforced against the `railpulse.api_usage` table — no
  Redis dependency.
- **Data lives in Supabase** inside a dedicated `railpulse` schema, sharing
  the same project as TrainPool. See
  `supabase/migrations/0001_railpulse_init.sql`.

Frontend, auth, Razorpay, and the LightGBM trained model are all Weekend 2+.

## Stack

- FastAPI (Python 3.12) + Uvicorn
- SQLAlchemy 2.0 async + asyncpg
- Supabase Postgres (shared project with TrainPool, `railpulse` schema)
- RapidAPI wrappers for public PNR data (IRCTC1 primary, fallback)
- Railway for hosting — see `DEPLOY.md`

## Project layout

```
railpulse/
├── app/
│   ├── main.py                     # FastAPI entry (create_app + /health)
│   ├── config.py                   # Settings via pydantic-settings
│   ├── api/
│   │   ├── predict.py              # POST /v1/predict
│   │   ├── pnr.py                  # /v1/pnr/track + /v1/pnr/{pnr}
│   │   ├── model_card.py           # GET /v1/model-card
│   │   ├── rate_limit.py           # free-tier caps (DB-backed, in-memory fallback for tests)
│   │   └── schemas.py              # Pydantic request/response models
│   ├── db/
│   │   ├── connection.py           # async engine + session factory
│   │   └── repositories/           # thin data access: predictions, pnrs, trains, api_usage
│   ├── data/
│   │   └── rapidapi_client.py      # dual-provider PNR adapter
│   └── ml/
│       ├── features.py             # feature engineering (shared train/serve)
│       ├── predict.py              # prediction wrapper with heuristic fallback
│       └── train_v0.py             # optional cold-start trainer (not wired in v0)
├── supabase/
│   └── migrations/
│       └── 0001_railpulse_init.sql
├── tests/
├── Dockerfile
├── pyproject.toml
├── .env.example
└── DEPLOY.md
```

## Local setup

```bash
# 1. Python 3.12 env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Env vars
cp .env.example .env
# Fill RAPIDAPI_KEY and DATABASE_URL (Supabase pooler)

# 3. Run the migration once against Supabase
# Paste supabase/migrations/0001_railpulse_init.sql into the Supabase SQL editor

# 4. Run
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the Swagger UI.

## Tests

```bash
pytest -q          # runs in-process, no DB required
ruff check .
mypy app/ --ignore-missing-imports
```

The test suite uses an in-memory rate-limit counter and `settings.disable_db=True`
so it runs without Postgres.

## The model card

`GET /v1/model-card` returns:

- The current `model_version` (v0: `v0-heuristic`)
- A plain-English methodology description
- The feature list
- Known limitations (we're explicit that v0 is a hand-tuned heuristic, not a trained model)
- Disclaimer
- Once `railpulse.model_eval_snapshots` has rows: Brier score, AUC, sample size, calibration curve

This endpoint is the trust differentiator vs. closed-source competitors like Confirmtkt.

## Legal posture

- We do not log into IRCTC
- We do not submit booking forms
- We consume public PNR data through RapidAPI's IRCTC wrappers
- Predictions are probabilistic estimates, not guarantees
- DPDP-compliant: client IPs are hashed with SHA-256 + server salt before being used as rate-limit keys
