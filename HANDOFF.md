# RailPulse v0 — Handoff

Branch: `claude/railpulse-v0-spec-GiQIH`

## What was built

**Database migration**
- `railpulse/supabase/migrations/0001_railpulse_init.sql` — new `railpulse` schema
  in the shared Supabase project (same project as TrainPool). Six tables:
  `trains`, `pnrs`, `pnr_status_history`, `predictions`, `api_usage`,
  `model_eval_snapshots`. No TimescaleDB. Idempotent. Permissions granted to
  `anon`, `authenticated`, `service_role`.
- The old `app/db/schema.sql` is replaced with a deprecation stub pointing at
  the new migration.

**Database wiring**
- `app/db/connection.py` — async SQLAlchemy engine + session factory. Auto-
  normalizes sync URLs (`postgresql+psycopg://`) to async (`+asyncpg`) so the
  `.env.example` URL works for both sync tooling and the async runtime.
  `pool_pre_ping=True` to survive Supabase pooler connection recycling.
  Includes a test hook `override_engine`.
- `app/db/repositories/` — thin SQL wrappers:
  - `predictions.py` — `log_prediction`, `find_pending_eval`, `update_outcome`
  - `pnrs.py` — `upsert_pnr`, `record_status`, `mark_chart_prepared`,
    `find_due_for_polling`, `count_tracked_for_subject`
  - `trains.py` — `get`, `get_or_create`, `update_stats`, plus a
    `PREMIUM_TRAIN_PREFIXES` list and `guess_is_premium` helper used as a
    day-1 prior for unseen trains
  - `api_usage.py` — `increment_predictions`, `increment_tracked_pnrs`,
    `get_usage` for rate-limit enforcement

**API refactor**
- `app/main.py` slimmed down to `create_app()` + `/health`. It mounts three
  routers.
- `app/api/predict.py` — `POST /v1/predict`. Rate-limit dep → train lookup/
  lazy-create → heuristic model → prediction logged with full feature dict.
- `app/api/pnr.py` — `POST /v1/pnr/track` + `GET /v1/pnr/{pnr}`. Track path
  hits RapidAPI, lazy-seeds the train row, upserts the PNR, appends status
  history, marks chart-prepared when applicable. Get path reads from our own
  tables only (no upstream call).
- `app/api/model_card.py` — `GET /v1/model-card`. Reads most recent row from
  `railpulse.model_eval_snapshots`, falls back to a static `models/v0_eval.json`
  if present, otherwise returns the honest "v0 heuristic — here's our
  methodology, we don't have eval numbers yet" response.
- `app/api/schemas.py` — Pydantic request/response models shared across
  routers and the OpenAPI docs.
- `app/api/rate_limit.py` — `enforce_prediction_rate_limit` and
  `enforce_track_pnr_rate_limit` FastAPI deps. Hash-salts client IPs with the
  server SECRET_KEY so we never store raw IPs. Uses the DB by default; falls
  back to an in-process counter when `settings.disable_db=True` so the test
  suite can exercise the 429 path without Postgres.

**Tests** (34 passing, pytest runs in ~2s without any DB)
- `tests/conftest.py` — builds the app with `disable_db=True`, overrides the
  `get_session` dep with a no-op async generator, resets the in-memory
  rate-limit state between tests.
- `tests/test_features.py` (15 tests) — feature engineering coverage:
  feature-version stamping, past-date clamping, extreme WL buckets, festive
  week detection, premium propagation, class one-hots, numeric coercion,
  parametrized booking urgency buckets.
- `tests/test_predict.py` (8 tests) — heuristic prediction wrapper: prob in
  [0,1], CI brackets prob, bucket label, monotonicity (WL 3 ≥ WL 150),
  warning emitted when model is not loaded, confidence band widens for
  low observation counts.
- `tests/test_api_predict.py` (5 tests) — FastAPI TestClient hits `/v1/predict`
  + validation rejection + `/health` + `/v1/model-card`.
- `tests/test_api_pnr.py` (4 tests) — stub `PnrClient` via
  `dependency_overrides`, happy path + validation + upstream 502.
- `tests/test_rate_limit.py` (2 tests) — 6th /v1/predict returns 429; 3rd
  /v1/pnr/track returns 429.

**Infra / docs**
- `Dockerfile` — multi-stage build, python:3.12-slim, non-root user, healthcheck,
  honors Railway's `$PORT`. `.dockerignore` excludes tests, .git, models, venv.
- `.github/workflows/railpulse-ci.yml` — runs ruff + mypy + pytest on any push
  touching `railpulse/**` or the workflow itself. Uses pip cache keyed on
  `pyproject.toml`.
- `DEPLOY.md` — step-by-step Railway deploy (monorepo root dir = `railpulse`,
  env var table, pooler vs direct URL note, custom domain, verification
  curls, operational caveats re: rate limit NAT collisions, RapidAPI quotas,
  and Supabase free-tier growth).
- `README.md` rewritten to reflect v0 reality — API-only, heuristic not
  LightGBM, Supabase shared with TrainPool, no Redis dependency.
- `pyproject.toml` — dropped LightGBM/sklearn/pandas/MLflow from core deps
  into an optional `[ml]` extra; added `sqlalchemy[asyncio]`, `asyncpg`,
  `greenlet`; configured ruff rules (`B008` ignored because FastAPI uses
  `Depends()` in argument defaults by design) and mypy defaults.
- `.env.example` — Supabase pooler format with the `abhfkspbjgxnorbeeqbo`
  project ref, `MODEL_VERSION=v0-heuristic`.

## What passes

```
$ ruff check .
All checks passed!

$ mypy app/ --ignore-missing-imports
Success: no issues found in 22 source files

$ pytest -q
34 passed in 1.93s
```

## What I skipped and why

- **Celery polling task stub** — nice-to-have in the spec. Skipped because
  Weekend 2 will rewrite the scheduling layer anyway and I didn't want to
  bake in a celery app factory we'd immediately tear out. The
  `find_due_for_polling` repo method is ready for it.
- **`app/ml/eval.py`** — nice-to-have. Skipped for the same reason: no eval
  data exists until we've collected predictions + chart outcomes, which
  needs real traffic. Writing the pipeline now means guessing at the shape
  of data we haven't seen.
- **`scripts/seed_trains.py`** — skipped, but the same effect is achieved
  with a hand-curated `PREMIUM_TRAIN_PREFIXES` list in
  `app/db/repositories/trains.py` and the `get_or_create` path that
  auto-seeds unseen trains with `is_premium` inferred from the prefix.
- **LightGBM / logistic model training** — explicitly out of scope per the
  spec ("v0 is heuristic only. Don't train a model. Ship the API.").
  `app/ml/train_v0.py` is untouched.
- **Docker build verification** — I can't run `docker build` in this
  sandbox. The Dockerfile is straightforward multi-stage slim Python with
  explicit pinned deps matching `pyproject.toml`, but someone should run
  `docker build -t railpulse .` once before the Railway deploy.

## Decisions I made that weren't spelled out in the spec

1. **`owner_user_id` is nullable and has no FK.** The spec says "nullable"
   but didn't specify the FK question. Since Supabase's `auth.users` table
   lives in a schema we don't control, putting a cross-schema FK would be
   brittle. Nullable UUID with no constraint — we'll validate membership in
   application code when auth lands.
2. **`api_usage` uses a single `subject_key TEXT` column** instead of the
   `COALESCE(user_id::TEXT, ip_hash)` PK from the old schema. Same semantics,
   simpler indexing, easier to query. For v0 everyone is an `ip:<hash>`
   subject.
3. **Added a `tracked_pnr_count` column to `api_usage`** for the per-day
   tracked-PNR cap. The spec mentioned both caps but left the storage
   implementation open — stuffing both counters into one row keeps the
   primary key simple.
4. **Added `settings.disable_db` escape hatch** for tests. Lets the test
   suite run entirely in-process with zero Postgres dependency. It's not
   exposed in `.env.example` so prod can't accidentally flip it on.
5. **`RailPulseModel` warning text is "Model not loaded — using fallback
   heuristic. Trust these predictions less."** — matched test expectations
   after slight wording checks.
6. **Pooler URL is the default in `.env.example`** per spec step 3 in the
   "Questions to send back" section. If asyncpg vs transaction-mode pooler
   friction appears in prod, `DEPLOY.md` documents the fallback path
   (session-mode pooler or direct URL).
7. **`app/db/schema.sql` was not deleted** — I replaced its contents with a
   deprecation stub pointing at the new migration. Safer than deleting in
   case external tooling references it.

## Open questions for the next session

1. **auth.users FK for `owner_user_id`?** I left it as a bare nullable UUID.
   When Supabase auth is wired up, do we want a deferred FK or just app-layer
   validation?
2. **When do we start logging the X-Forwarded-For source?** Currently we only
   hash it into the rate-limit key. If we want to detect NAT collisions we'd
   need to sample and store something more granular, which has privacy
   implications.
3. **Should the `pnr_status_history` table have a retention policy?**
   Supabase free tier gives 500MB; at say 10 polls/PNR × 200 bytes × many
   PNRs this table will grow fast. DEPLOY.md flags this but there's no
   actual prune job yet.
4. **RapidAPI schemas** — the existing adapter's field mapping is guessed,
   not verified. First real call should log the raw response and we should
   tighten the normalizer based on what we actually see.
5. **Is `MODEL_VERSION=v0-heuristic`** what we want surfaced on the model
   card, or do we want something with a date suffix (`v0-heuristic-2026-04`)
   so we can distinguish heuristic tunings in the logs?

## How to resume

```bash
# 1. Run the migration in the Supabase SQL editor (project abhfkspbjgxnorbeeqbo)
#    paste railpulse/supabase/migrations/0001_railpulse_init.sql

# 2. Set env vars locally
cp railpulse/.env.example railpulse/.env
# edit: DATABASE_URL, RAPIDAPI_KEY, SECRET_KEY

# 3. Run locally
cd railpulse
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# 4. Deploy to Railway — follow DEPLOY.md
```

Before merging to `main`, check:
- [ ] Supabase migration runs cleanly (copy-paste into SQL editor)
- [ ] `docker build -t railpulse .` succeeds locally
- [ ] GitHub Actions workflow goes green on the PR
