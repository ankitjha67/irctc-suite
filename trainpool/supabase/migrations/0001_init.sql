-- TrainPool schema v1.0
-- Run this in your Supabase SQL editor

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users (organizers only; members are anonymous)
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trips
CREATE TABLE IF NOT EXISTS trips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  organizer_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  train_number TEXT,
  travel_date DATE NOT NULL,
  deadline TIMESTAMPTZ NOT NULL,
  expected_count INT CHECK (expected_count BETWEEN 1 AND 20),
  id_proof_required BOOLEAN DEFAULT FALSE,
  status TEXT DEFAULT 'active' CHECK (status IN ('active','locked','booked','expired')),
  auto_delete_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trips_organizer ON trips(organizer_id);
CREATE INDEX IF NOT EXISTS idx_trips_auto_delete ON trips(auto_delete_at) WHERE status != 'expired';

-- Passengers (anonymous members)
CREATE TABLE IF NOT EXISTS passengers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID REFERENCES trips(id) ON DELETE CASCADE NOT NULL,
  full_name TEXT NOT NULL CHECK (char_length(full_name) BETWEEN 2 AND 80),
  age INT NOT NULL CHECK (age BETWEEN 1 AND 120),
  gender CHAR(1) NOT NULL CHECK (gender IN ('M','F','T')),
  berth_preference TEXT CHECK (berth_preference IN ('LB','MB','UB','SL','SU','NP') OR berth_preference IS NULL),
  id_type TEXT CHECK (id_type IN ('AADHAAR','PAN','DL','PASSPORT','VOTER') OR id_type IS NULL),
  id_number_encrypted BYTEA,   -- AES-256-GCM payload: 12-byte IV || ciphertext || 16-byte tag
  id_number_hint TEXT,          -- e.g., "****1234" for display in dashboard
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  last_edit_at TIMESTAMPTZ DEFAULT NOW(),
  edit_token_hash TEXT NOT NULL -- sha256(edit_token), never store raw token
);

CREATE INDEX IF NOT EXISTS idx_passengers_trip ON passengers(trip_id);

-- Row Level Security
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE passengers ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policies: trips
-- Organizers can fully manage their own trips
CREATE POLICY trips_organizer_all ON trips
  FOR ALL
  USING (organizer_id = auth.uid())
  WITH CHECK (organizer_id = auth.uid());

-- Public can read trip metadata by slug (for the join page) — limited to non-sensitive cols via the API layer
CREATE POLICY trips_public_read ON trips
  FOR SELECT
  USING (true);

-- Policies: passengers
-- Organizers can read passengers of their trips
CREATE POLICY passengers_organizer_read ON passengers
  FOR SELECT
  USING (
    EXISTS (SELECT 1 FROM trips WHERE trips.id = passengers.trip_id AND trips.organizer_id = auth.uid())
  );

-- Anyone can insert a passenger (join a trip) — app layer validates slug + deadline
CREATE POLICY passengers_public_insert ON passengers
  FOR INSERT
  WITH CHECK (true);

-- Updates require the app layer to verify edit_token_hash — RLS alone cannot do this, so we rely on service role for updates
-- (Next.js API routes will use the service role key for passenger edits + edit_token verification in app code)

-- Auto-delete cron
-- Supabase pg_cron:
--   SELECT cron.schedule('trainpool-autodelete', '0 * * * *',
--     $$DELETE FROM trips WHERE auto_delete_at < NOW()$$);
