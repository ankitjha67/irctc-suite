-- RailPulse schema v0
-- Lives inside the existing Supabase project (shared with TrainPool) under a
-- dedicated `railpulse` schema so there's no collision with TrainPool tables
-- in `public`.
--
-- Supabase free tier does not include TimescaleDB — we use plain Postgres
-- with careful indexes. The `pnr_status_history` table is a regular table
-- (not a hypertable) which is fine for the first 10K–50K rows.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS railpulse;

-- ─── Trains reference ────────────────────────────────────────────────────────
-- Seeded lazily as we observe new trains. The eval job updates the rolling
-- cancellation stats and observation count.
CREATE TABLE IF NOT EXISTS railpulse.trains (
  train_number TEXT PRIMARY KEY,
  train_name TEXT,
  source_station TEXT,
  dest_station TEXT,
  is_premium BOOLEAN DEFAULT FALSE,
  route_length_km INT,
  runs_on_dow TEXT,                    -- 7-char mask, e.g. '1111111' for daily
  avg_cancellation_rate FLOAT,         -- rolling 90d, updated by eval job
  observation_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Tracked PNRs ────────────────────────────────────────────────────────────
-- owner_user_id is nullable for v0 (no auth yet). When auth lands we'll
-- populate it from the JWT without requiring a schema migration.
CREATE TABLE IF NOT EXISTS railpulse.pnrs (
  pnr TEXT PRIMARY KEY,
  train_number TEXT REFERENCES railpulse.trains(train_number),
  travel_date DATE NOT NULL,
  source TEXT,
  destination TEXT,
  class TEXT,
  quota TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  chart_prepared_at TIMESTAMPTZ,
  final_status TEXT,                   -- CNF / RAC / WL / CAN — filled at chart prep
  owner_user_id UUID,                  -- nullable in v0, no FK since auth.users lives in a different schema
  poll_count INT DEFAULT 0,
  last_polled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_railpulse_pnrs_polling_queue
  ON railpulse.pnrs (last_polled_at NULLS FIRST)
  WHERE chart_prepared_at IS NULL AND travel_date >= CURRENT_DATE;

CREATE INDEX IF NOT EXISTS idx_railpulse_pnrs_owner
  ON railpulse.pnrs (owner_user_id);

-- ─── PNR status history ──────────────────────────────────────────────────────
-- Each poll writes a row here. Composite index on (pnr, observed_at DESC)
-- lets us read the WL trajectory for a single PNR in O(log n).
CREATE TABLE IF NOT EXISTS railpulse.pnr_status_history (
  id BIGSERIAL PRIMARY KEY,
  pnr TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  wl_position INT,                     -- NULL if CNF/RAC
  status_code TEXT NOT NULL,           -- WL / CNF / RAC / CAN
  status_text TEXT,                    -- raw text, e.g. 'WL 12'
  raw_response JSONB
);

CREATE INDEX IF NOT EXISTS idx_railpulse_pnr_history_pnr
  ON railpulse.pnr_status_history (pnr, observed_at DESC);

-- ─── Predictions log ─────────────────────────────────────────────────────────
-- Every /v1/predict call writes a row here so we can build a labeled training
-- set once chart prep happens for the matching PNRs.
CREATE TABLE IF NOT EXISTS railpulse.predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pnr TEXT,
  user_id UUID,
  features JSONB NOT NULL,
  predicted_prob FLOAT NOT NULL CHECK (predicted_prob BETWEEN 0 AND 1),
  predicted_bucket TEXT CHECK (predicted_bucket IN ('high','medium','low')),
  confidence_lo FLOAT,
  confidence_hi FLOAT,
  model_version TEXT NOT NULL,
  made_at TIMESTAMPTZ DEFAULT NOW(),
  actual_outcome TEXT,                 -- filled post chart prep
  scored_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_railpulse_predictions_pending_eval
  ON railpulse.predictions (made_at) WHERE actual_outcome IS NULL;

CREATE INDEX IF NOT EXISTS idx_railpulse_predictions_eval_window
  ON railpulse.predictions (scored_at) WHERE actual_outcome IS NOT NULL;

-- ─── Rate limiting ───────────────────────────────────────────────────────────
-- Supabase free tier has no Redis. We enforce rate limits at the app layer
-- with a simple insert-or-increment against this table. Swap for Redis when
-- traffic justifies it.
CREATE TABLE IF NOT EXISTS railpulse.api_usage (
  subject_key TEXT NOT NULL,           -- user_id::text OR ip_hash
  day DATE NOT NULL,
  prediction_count INT DEFAULT 0,
  tracked_pnr_count INT DEFAULT 0,
  PRIMARY KEY (subject_key, day)
);

-- ─── Model eval snapshots ────────────────────────────────────────────────────
-- Powers the public model card endpoint.
CREATE TABLE IF NOT EXISTS railpulse.model_eval_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version TEXT NOT NULL,
  evaluated_at TIMESTAMPTZ DEFAULT NOW(),
  sample_size INT,
  brier_score FLOAT,
  auc_roc FLOAT,
  calibration_curve JSONB,             -- array of {bucket, predicted_mean, actual_rate, n}
  top_1_accuracy FLOAT,
  notes TEXT
);

-- ─── Permissions ─────────────────────────────────────────────────────────────
-- The FastAPI service connects as the `postgres` role via the Supabase pooler
-- so it has full access regardless. These grants exist so that — if later we
-- wire up PostgREST for a /rest/v1/railpulse.* surface — the anon/authenticated
-- roles can at least enumerate the schema. Actual row access is still gated by
-- RLS (not enabled in v0 since there's no end-user write path).
GRANT USAGE ON SCHEMA railpulse TO anon, authenticated, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA railpulse TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA railpulse TO service_role;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA railpulse TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA railpulse
  GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA railpulse
  GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA railpulse
  GRANT USAGE, SELECT ON SEQUENCES TO service_role;
