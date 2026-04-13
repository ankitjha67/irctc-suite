-- RailPulse schema v1.0
-- Requires TimescaleDB extension (install via Railway add-on or:
--   CREATE EXTENSION IF NOT EXISTS timescaledb;)

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Users (magic-link auth via Supabase or own impl)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  tier TEXT DEFAULT 'free' CHECK (tier IN ('free','pro')),
  pro_until TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trains reference (seeded from Indian Railways public train list)
CREATE TABLE IF NOT EXISTS trains (
  train_number TEXT PRIMARY KEY,
  train_name TEXT,
  source_station TEXT,
  dest_station TEXT,
  is_premium BOOLEAN DEFAULT FALSE,
  route_length_km INT,
  runs_on_dow TEXT,              -- 7-char mask, e.g. '1111111' for daily
  avg_cancellation_rate FLOAT,   -- rolling 90d, updated by eval job
  observation_count INT DEFAULT 0
);

-- Tracked PNRs
CREATE TABLE IF NOT EXISTS pnrs (
  pnr TEXT PRIMARY KEY,
  train_number TEXT REFERENCES trains(train_number),
  travel_date DATE NOT NULL,
  source TEXT,
  destination TEXT,
  class TEXT,
  quota TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  chart_prepared_at TIMESTAMPTZ,
  final_status TEXT,             -- CNF / RAC / WL / CAN — filled at chart prep
  owner_user_id UUID REFERENCES users(id),
  poll_count INT DEFAULT 0,
  last_polled_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_pnrs_polling_queue
  ON pnrs (last_polled_at NULLS FIRST)
  WHERE chart_prepared_at IS NULL AND travel_date >= CURRENT_DATE;

CREATE INDEX IF NOT EXISTS idx_pnrs_owner ON pnrs(owner_user_id);

-- Time-series: WL movement history (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS pnr_status_history (
  pnr TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  wl_position INT,                -- NULL if CNF/RAC
  status_code TEXT NOT NULL,      -- WL / CNF / RAC / CAN
  status_text TEXT,               -- raw text, e.g. 'WL 12'
  raw_response JSONB
);

SELECT create_hypertable('pnr_status_history', 'observed_at', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_pnr_history_pnr ON pnr_status_history (pnr, observed_at DESC);

-- Predictions log (used for weekly eval + model calibration)
CREATE TABLE IF NOT EXISTS predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pnr TEXT,
  user_id UUID REFERENCES users(id),
  features JSONB NOT NULL,
  predicted_prob FLOAT NOT NULL CHECK (predicted_prob BETWEEN 0 AND 1),
  predicted_bucket TEXT CHECK (predicted_bucket IN ('high','medium','low')),
  confidence_lo FLOAT,            -- 10th percentile
  confidence_hi FLOAT,            -- 90th percentile
  model_version TEXT NOT NULL,
  made_at TIMESTAMPTZ DEFAULT NOW(),
  actual_outcome TEXT,            -- filled post chart prep
  scored_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_predictions_pending_eval
  ON predictions(made_at) WHERE actual_outcome IS NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_eval_window
  ON predictions(scored_at) WHERE actual_outcome IS NOT NULL;

-- Rate limiting (Redis preferred, but fallback table)
CREATE TABLE IF NOT EXISTS api_usage (
  user_id UUID,
  ip_hash TEXT,
  day DATE NOT NULL,
  prediction_count INT DEFAULT 0,
  PRIMARY KEY (COALESCE(user_id::TEXT, ip_hash), day)
);

-- Model eval snapshots (public model card data source)
CREATE TABLE IF NOT EXISTS model_eval_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  model_version TEXT NOT NULL,
  evaluated_at TIMESTAMPTZ DEFAULT NOW(),
  sample_size INT,
  brier_score FLOAT,
  auc_roc FLOAT,
  calibration_curve JSONB,        -- array of {bucket, predicted_mean, actual_rate, n}
  top_1_accuracy FLOAT,
  notes TEXT
);
