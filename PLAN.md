# IRCTC Companion Suite — Master Plan

**Author:** Ankit Jha
**Date:** April 2026
**Framework:** product-architect (Agents 02, 03, 04, 06, 09, 11, 14, 18, 29)
**Status:** Draft v1.0

> Two legitimate, shippable products that solve real IRCTC pain without touching the booking automation trip-wire. RailPulse is the intelligence layer. TrainPool is the coordination layer. Together they're a companion suite — never a replacement for IRCTC, never a booking bot.

---

## 0. Portfolio Positioning

| | **RailPulse** | **TrainPool** |
|---|---|---|
| **One-liner** | Waitlist confirmation prediction + PNR tracking | Collect group passenger details without shared IRCTC logins |
| **Core loop** | User queries → ML predicts WL→CNF probability → alerts on change | Organizer creates trip → members fill own details → paste-ready block |
| **Legal posture** | Read-only data consumer, no IRCTC credentials, no scraping at scale | Zero IRCTC integration — pure coordination tool, data never leaves TrainPool |
| **Primary moat** | Historical dataset + calibrated probability model | UX + privacy-first (auto-delete, no accounts required for members) |
| **Comparable** | Confirmtkt, ixigo prediction, RailYatri | None direct — people use WhatsApp + Google Forms today |
| **Monetization** | Freemium (5 free predictions/day → ₹99/mo Pro) | Free forever (lead gen into RailPulse Pro) |
| **Stack fit with your portfolio** | FastAPI + PostgreSQL + ML (like BASEL-III engine) | Next.js + Supabase (new learning, closer to TrailSync Flutter work) |

**Strategic sequencing:** Build TrainPool first (2 weekends, simpler, ships fast, gives you a userbase). Then build RailPulse (4–5 weekends, more complex, uses TrainPool users as the acquisition channel).

---

# PART I: TRAINPOOL

## 1. Overview

### 1.1 Problem Statement
Booking group train tickets on IRCTC requires all passenger details (name, age, gender, berth preference, ID proof) from every member. Today, the organizer chases people on WhatsApp, gets replies in free text across 12 messages, and manually copies into the IRCTC form under Tatkal time pressure. Errors are common, privacy is non-existent (names/ages in a group chat), and the typing burden sits entirely on the organizer.

**Evidence:** Reddit r/india and r/indianrailways have recurring posts about group booking frustration. Your own travel group likely does this on WhatsApp. The pattern is universal during festive/holiday bookings.

### 1.2 Goals
- **Primary:** Reduce group booking passenger-detail-collection time from ~20 min to under 3 min
- **Secondary:** Eliminate data-entry errors during Tatkal window; preserve member privacy

### 1.3 Non-Goals (Explicitly Out of Scope)
- No IRCTC login, session handling, or form submission — this is a **coordination tool**, not a booking tool
- No payment handling in v1
- No chat/messaging — use existing WhatsApp/Signal for comms
- No seat/berth selection negotiation — just data collection

### 1.4 Success Metrics
| Metric | Target (3 months) | Measurement |
|---|---|---|
| Trips created | 500 | Supabase row count |
| Avg members per trip | 3.5 | Avg passengers joined / trip |
| Completion rate (all members filled before deadline) | 70% | trip.status = 'complete' |
| Time from trip create → paste block ready | Median < 8 min | Timestamp diff |
| NPS (simple thumbs up/down on completion screen) | > 60% positive | Self-reported |

---

## 2. User Stories

**Personas:**
1. **Priya the Organizer** (28, Bangalore, books group trips for 4–8 friends or family 3–4× a year)
2. **Rohan the Member** (24, works elsewhere, gets a link from Priya, just needs to fill his stuff fast)

| ID | As a... | I want to... | So that... | Priority |
|---|---|---|---|---|
| US-001 | Organizer | Create a trip with train details + deadline | Members know what they're joining | P0 |
| US-002 | Organizer | Share a single link to all members | No back-and-forth chasing | P0 |
| US-003 | Member | Fill my details on my phone in under 60 sec | I don't have to type on a laptop | P0 |
| US-004 | Organizer | See who has/hasn't filled details | I can chase the stragglers | P0 |
| US-005 | Organizer | Get a paste-ready passenger block | I can paste it into IRCTC in one go | P0 |
| US-006 | Member | Not create an account | I don't care about another login | P0 |
| US-007 | Organizer | Set auto-delete (24h after trip date) | My family's data doesn't sit on servers | P0 |
| US-008 | Organizer | Reuse my own saved passenger profile | I'm in every trip I create | P1 |
| US-009 | Member | Edit my details after submitting | I made a typo on age | P1 |
| US-010 | Organizer | Export passenger block as CSV | If pasting fails I have a backup | P2 |

### 2.3 Acceptance Criteria (US-005, the money feature)

```
US-005: Paste-ready block generation
- GIVEN all members have submitted details AND trip has ≥1 passenger
  WHEN organizer clicks "Generate Booking Block"
  THEN system outputs a formatted block with columns: Name | Age | Gender | Berth Pref | ID Type | ID No
  AND the block matches IRCTC's tab-separated paste format
  AND the block opens in a modal with "Copy" button
  AND copying triggers a success toast + "Now paste into IRCTC" helper

- GIVEN some members have NOT submitted
  WHEN organizer clicks "Generate Booking Block"
  THEN system shows warning: "3 of 5 members haven't submitted. Generate anyway?"
  AND lists the missing members

- GIVEN a member submits an invalid age (>120 or <1)
  WHEN the form is submitted
  THEN validation fails with a field-level error
  AND the submission is not saved
```

---

## 3. Key Flows

### 3.1 Organizer flow
```
1. Land on / → "Create a trip" CTA
2. Fill minimal trip meta:
   - Trip name ("Goa New Year")
   - Train number (optional, free text)
   - Travel date
   - Number of expected passengers
   - Deadline for members to fill (auto-default: 24h before travel)
3. System generates trip with unique 6-char slug: /trip/goa-x7k9
4. Organizer fills own details as first passenger
5. Share screen: copy link, copy WhatsApp message template, QR code
6. Dashboard: live status of each member (pending / filled / needs review)
7. When ready → Generate Block → Copy → Paste into IRCTC
8. Optional: "Mark trip as booked" (triggers auto-delete scheduler)
```

### 3.2 Member flow
```
1. Tap link from WhatsApp → mobile-optimized form
2. See trip context: "Priya is booking Goa New Year for 5 people. Deadline: 31 Dec 10 PM"
3. Fill form (autofilled if localStorage has prior profile):
   - Full name (as per ID)
   - Age
   - Gender (M/F/T)
   - Berth preference (Lower/Middle/Upper/SL/SU/No pref)
   - ID type (Aadhaar/PAN/DL/Passport/Voter) — optional unless organizer required it
   - ID number — masked input, stored encrypted, shown to organizer only in final block
4. Submit → "Done! Priya will see your details." + option to save profile locally for next time
5. Can re-open same link to edit until deadline
```

### 3.3 Edge cases to design for
- Member opens link on desktop → still works, same form
- Organizer creates trip, never comes back → trip auto-deletes after 7 days of inactivity
- Deadline passes → form locks, organizer sees "expired — extend?" button
- Same member fills twice (different devices) → last-write-wins with warning banner
- Link leaked to wrong person → organizer can revoke any passenger + rotate slug

---

## 4. Technical Architecture

### 4.1 Stack decision matrix

| Concern | Choice | Why |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | Fullstack in one codebase, SSR for SEO, deploys to Vercel free tier |
| Database | **Supabase (Postgres)** | Free tier is generous, Row Level Security maps cleanly to trip/slug access model, realtime subscriptions for the organizer dashboard |
| Auth | **Supabase Auth (magic link, organizers only)** | Members stay anonymous — this is the key privacy promise |
| Encryption | **AES-256-GCM via `node:crypto`** | ID numbers encrypted at rest with per-trip key derived from slug + app secret |
| Hosting | **Vercel** | Free tier covers v1, edge functions for the slug resolver |
| Email (deadline reminders) | **Resend** | 3K emails/month free, clean API |
| Analytics | **PostHog self-hosted or Plausible** | Privacy-respecting, no Google Analytics on a privacy-first product |
| Domain | `trainpool.in` or `.app` (check availability) | Short, memorable |

### 4.2 Data model

```sql
-- Organizers are the only real users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,  -- 6-char nanoid, e.g. 'goa-x7k9'
  organizer_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  train_number TEXT,
  travel_date DATE NOT NULL,
  deadline TIMESTAMPTZ NOT NULL,
  expected_count INT,
  id_proof_required BOOLEAN DEFAULT FALSE,
  status TEXT DEFAULT 'active' CHECK (status IN ('active','locked','booked','expired')),
  auto_delete_at TIMESTAMPTZ,   -- set to travel_date + 24h
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE passengers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID REFERENCES trips(id) ON DELETE CASCADE,
  full_name TEXT NOT NULL,
  age INT NOT NULL CHECK (age BETWEEN 1 AND 120),
  gender CHAR(1) CHECK (gender IN ('M','F','T')),
  berth_preference TEXT,
  id_type TEXT,
  id_number_encrypted BYTEA,  -- AES-256-GCM, key derived per-trip
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  last_edit_at TIMESTAMPTZ DEFAULT NOW(),
  edit_token TEXT NOT NULL    -- lets the same device re-edit without auth
);

CREATE INDEX idx_passengers_trip ON passengers(trip_id);
CREATE INDEX idx_trips_auto_delete ON trips(auto_delete_at) WHERE status != 'expired';

-- RLS: organizers see only their trips; public reads allowed only by slug
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE passengers ENABLE ROW LEVEL SECURITY;
```

### 4.3 API surface (Next.js route handlers)
- `POST /api/trips` — create trip (auth required)
- `GET /api/trips/[slug]` — public metadata (no PII, just name/deadline/count)
- `POST /api/trips/[slug]/passengers` — add passenger (public, returns edit_token)
- `PATCH /api/trips/[slug]/passengers/[id]` — edit (requires edit_token cookie)
- `GET /api/trips/[slug]/dashboard` — organizer view (auth + ownership check)
- `POST /api/trips/[slug]/generate-block` — organizer-only, returns formatted block

### 4.4 The paste-block generator

IRCTC's "Passenger Details" form accepts this tab-separated shape when you paste into the first field (this is the standard IRCTC browser behavior — not a scraping-level integration, just clipboard format):

```
Name<TAB>Age<TAB>Gender<TAB>BerthPref<TAB>IDType<TAB>IDNumber
```

The generator:
1. Validates all passengers present
2. Decrypts ID numbers with per-trip key
3. Formats as TSV + human-readable table
4. Logs generation event (for the trip timeline, not for ad tracking)
5. Returns both formats for the modal

> **Important:** The block is generated on-demand, never stored as a derived artifact. This way, if someone exfiltrates the DB they get encrypted ID numbers, not a ready-to-use passenger dump.

### 4.5 Auto-delete cron
Supabase pg_cron job runs hourly:
```sql
DELETE FROM trips WHERE auto_delete_at < NOW();
-- Cascade drops passengers too. No soft-delete.
```

---

## 5. Security & Compliance (Agent 09 + Agent 11)

| Concern | Mitigation |
|---|---|
| **DPDP Act 2023 applicability** | Yes — PII of individuals is processed. Mitigations: explicit consent on member form, purpose limitation (stated clearly), retention limit (auto-delete), data principal rights (edit/delete via edit_token) |
| **ID proof storage** | Only collected if organizer opts in, encrypted at rest with per-trip key, decrypted only at block-generation time, deleted on trip auto-delete |
| **Slug guessability** | 6-char nanoid = ~14 billion combos; rate-limit /trip/[slug] to 10 req/min per IP |
| **Edit token hijack** | Token is HttpOnly cookie, scoped to path, rotated on edit, revocable by organizer |
| **Data breach blast radius** | No central passenger list; each trip is an isolated silo with its own encryption key |
| **Accounts abuse** | Magic-link only, no passwords; rate-limit trip creation to 20/day per user |

**Privacy policy key points to publish:**
- We never share data with third parties
- We never sell data
- ID proofs are encrypted
- Everything auto-deletes after the trip
- Organizers can delete any trip at any time
- No cookies for tracking — only functional cookies

---

## 6. TrainPool Build Plan (2 weekends)

### Weekend 1: Core loop
- **Sat morning:** Repo setup, Supabase project, schema migration, Next.js scaffold with shadcn/ui
- **Sat afternoon:** Trip creation flow + organizer auth (magic link)
- **Sat evening:** Public passenger form + validation + edit_token cookie
- **Sun morning:** Organizer dashboard (live passenger list, Supabase realtime subscription)
- **Sun afternoon:** Generate Block modal + copy-to-clipboard + TSV formatting
- **Sun evening:** Deploy to Vercel, test end-to-end with your own WhatsApp group

### Weekend 2: Polish, privacy, ship
- **Sat morning:** ID encryption layer (per-trip key derivation)
- **Sat afternoon:** Auto-delete cron + deadline locking + email reminders via Resend
- **Sat evening:** Landing page (use anti-slop-design skill, zero emojis, real Unsplash, film grain)
- **Sun morning:** Privacy policy + terms + about page
- **Sun afternoon:** Share on your LinkedIn (28K audience) + post in r/indianrailways
- **Sun evening:** Monitor first users, fix whatever breaks

**Deliverable at end of W2:** Live at trainpool.in, first 10 real trips created, first LinkedIn post published.

---

---

# PART II: RAILPULSE

## 1. Overview

### 1.1 Problem Statement
Indian Railways runs 13,000+ trains daily with a waitlist system where a WL50 ticket sometimes confirms and a WL10 sometimes doesn't. Passengers have no reliable way to estimate their confirmation probability, so they either (a) book backup flights they don't need, (b) cancel and lose money, or (c) stress for weeks. Confirmtkt and ixigo offer paid versions of this — but the UX is cluttered and the models are black boxes.

**Evidence:** Confirmtkt has 10M+ app installs. The market has validated that people will open an app specifically for WL prediction. Your edge is a cleaner UX, a calibrated model (not just a number but a confidence interval), and a free tier that isn't pay-walled after one use.

### 1.2 Goals
- **Primary:** Predict P(WL→CNF) with calibration error < 10% on held-out data
- **Secondary:** Zero-friction PNR tracking with push alerts on status change

### 1.3 Non-Goals
- **No booking assistance** — this is explicitly a prediction + tracking tool
- **No Tatkal timing advice** — that drifts toward facilitation
- **No historical train route planning** — ixigo owns that space
- **No chatbot / LLM wrapper** — the ML model is the product

### 1.4 Success Metrics
| Metric | Target (6 months post-launch) | Measurement |
|---|---|---|
| Predictions served / day | 2,000 | API hit count |
| Calibration Brier score | < 0.15 | Weekly eval against actual outcomes |
| PNRs tracked | 15,000 | Unique PNR count |
| Free → Pro conversion | 3% | Razorpay subscription count |
| Model accuracy (top-1 bucket) | > 75% | Predicted bucket vs actual |

---

## 2. User Stories

**Personas:**
1. **Arjun the frequent traveler** (32, works in Bangalore, family in Patna, books 15+ trains/year, currently uses Confirmtkt)
2. **Meera the anxious first-timer** (21, student booking her first long-distance train alone, needs reassurance)

| ID | As a... | I want to... | So that... | Priority |
|---|---|---|---|---|
| US-101 | Traveler | Enter train number + date + WL position | I see my confirmation probability | P0 |
| US-102 | Traveler | Paste my PNR | It auto-fills and tracks | P0 |
| US-103 | Traveler | See historical WL→CNF movement for this train | I understand the pattern, not just a number | P0 |
| US-104 | Traveler | Get push notification when PNR status changes | I don't have to keep refreshing | P0 |
| US-105 | Anxious user | See a confidence interval, not just a %age | I can plan for worst case | P1 |
| US-106 | Frequent user | Save frequent trains (Rajdhani, Vande Bharat) | I don't re-enter them | P1 |
| US-107 | Pro user | Unlimited predictions + multi-PNR tracking | I book a lot | P2 |
| US-108 | Traveler | See alternative trains with better WL odds | I have backup options | P2 |

---

## 3. The ML Problem (Agent 29)

This is the actual interesting technical work. Let me be specific.

### 3.1 Problem formulation

**Given:** train_number, travel_date, source_station, dest_station, class (SL/3A/2A/1A/CC/EC), quota (GN/TQ/LD), booking_time, current_wl_position
**Predict:** P(status_at_chart_prep = CONFIRMED | features)

This is a **binary classification with probability calibration**, not just a score. The key is calibration — a predicted 70% should actually confirm 70% of the time over many predictions.

### 3.2 Feature engineering

| Feature category | Features |
|---|---|
| **Train-level** | train_number, avg_cancellation_rate_last_90d, route_length, is_premium (Rajdhani/Vande Bharat), days_of_week_pattern |
| **Temporal** | days_before_travel, day_of_week, is_festive_week, is_exam_season, is_holiday_weekend |
| **Position** | current_wl_position, wl_position_normalized (pos / class_capacity), booking_percentile |
| **Route** | source_station, dest_station, route_popularity_score, is_weekend_destination |
| **Class/quota** | class (one-hot), quota (one-hot), capacity_for_class |
| **Derived** | cancellation_velocity (avg WL drop per day on this train), peer_percentile (how your WL compares to typical at this booking time) |

### 3.3 Data acquisition strategy — the hardest part

**Problem:** No public historical waitlist movement dataset exists. Confirmtkt has this data because they polled PNRs for years. You need to bootstrap.

**Solution: Three-pronged data strategy**

**1. Synthetic cold-start (Weekend 1–2)**
- Kaggle has 1–2 older Indian Railways datasets (~100K PNR outcomes). Use these for v0 model training.
- Known public approximations: "WL drop rate ≈ 5–15% per day depending on train tier". Use these as priors in a Bayesian model.

**2. Build your own dataset from day 1 (ongoing)**
- Every time a user enters a WL position, you log `(train, date, wl_pos, timestamp)`.
- Cron job re-queries the same PNR daily via RapidAPI until chart prep.
- At chart prep, log final outcome → `(features, label)`.
- After 3 months you have ~5K–20K labeled examples (depends on traffic).
- **This is the defensible moat** — once you have it, no competitor can catch up without the same timeline.

**3. Partner/buy (if growth justifies it)**
- Kaggle competitions sometimes release railway data
- Academic partnerships with IITs working on transportation research
- Worst case: scrape your own usage data from public sources with proper rate limits

### 3.4 Model architecture

| Stage | Model | Why |
|---|---|---|
| **v0 (cold start, Weekend 3)** | Logistic regression with hand-crafted features | Interpretable, fast to train, low data requirement, easy to calibrate |
| **v1 (after 1K samples, Month 2)** | Gradient boosting (LightGBM or XGBoost) | Handles non-linear interactions, your BASEL-III work already uses these, well-calibrated with isotonic regression |
| **v2 (after 10K samples, Month 4+)** | LightGBM + per-train embedding layer | Captures train-specific idiosyncrasies |
| **v3 (future)** | Small transformer on PNR time-series | Only if v2 hits a ceiling |

**Calibration layer:** Always wrap with isotonic regression or Platt scaling on a held-out set. Report Brier score and calibration curves in the model card.

**Confidence intervals:** Use quantile regression or bootstrap resampling to report 10th/50th/90th percentile outcomes, not just point estimates. This is the "anxious Meera" feature.

### 3.5 Evaluation

```python
# Weekly eval pipeline (runs on Sundays)
# 1. Load all predictions made 7+ days ago where chart prep has happened
# 2. Compare predicted probability to actual outcome
# 3. Compute:
#    - Brier score (lower is better, < 0.15 target)
#    - Calibration curve (10 buckets, check diagonal alignment)
#    - AUC-ROC (should be > 0.80)
#    - Top-1 accuracy (predicted bucket vs actual outcome)
# 4. If calibration drift > 5%, trigger retraining
# 5. Publish public "model card" on the site with last eval
```

Publishing your calibration curve publicly is a trust moat Confirmtkt doesn't offer.

---

## 4. Technical Architecture (Agent 06)

### 4.1 Stack decision matrix

| Concern | Choice | Why |
|---|---|---|
| **Backend** | FastAPI + Python 3.12 | Your domain, already proven in baselkit + BASEL-III engine |
| **Frontend** | Next.js 15 (reuse TrainPool stack) | Same skills, fast iteration |
| **Primary DB** | PostgreSQL 16 | Standard relational for users/trips/PNRs |
| **Time-series** | TimescaleDB extension | WL movement data is inherently time-series, massive compression |
| **Cache** | Redis | API response cache (15 min TTL), rate limiting |
| **ML serving** | FastAPI in-process (LightGBM is fast) + ONNX runtime for v2+ | No separate model server needed at this scale |
| **Training** | Jupyter + MLflow for tracking | Your existing Python workflow |
| **Task queue** | Celery + Redis | PNR polling, scheduled retraining, alerts |
| **External data** | RapidAPI IRCTC1 wrapper (primary) + fallback to irctc-indian-railway-pnr-status | Two providers to avoid single point of failure |
| **Push notifications** | OneSignal free tier | Web push + Android, no server to maintain |
| **Payments** | Razorpay (you already know this from Maha Jyotish) | UPI native |
| **Hosting** | Railway or Fly.io | Your existing choice for TrailSync, cheap, good Postgres support |

### 4.2 Data model (core tables)

```sql
CREATE TABLE pnrs (
  pnr TEXT PRIMARY KEY,
  train_number TEXT NOT NULL,
  travel_date DATE NOT NULL,
  source TEXT,
  destination TEXT,
  class TEXT,
  quota TEXT,
  first_seen_at TIMESTAMPTZ DEFAULT NOW(),
  chart_prepared_at TIMESTAMPTZ,
  final_status TEXT,  -- CNF, CAN, WL, RAC
  owner_user_id UUID REFERENCES users(id)
);

-- TimescaleDB hypertable for WL movement
CREATE TABLE pnr_status_history (
  pnr TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  wl_position INT,
  status_text TEXT,
  raw_response JSONB
);
SELECT create_hypertable('pnr_status_history', 'observed_at');
CREATE INDEX ON pnr_status_history (pnr, observed_at DESC);

-- Predictions log for eval
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pnr TEXT,
  features JSONB,
  predicted_prob FLOAT,
  predicted_bucket TEXT,  -- 'high'/'medium'/'low'
  model_version TEXT,
  made_at TIMESTAMPTZ DEFAULT NOW(),
  actual_outcome TEXT,  -- filled at chart prep
  scored_at TIMESTAMPTZ
);

CREATE INDEX idx_predictions_eval ON predictions(made_at) WHERE actual_outcome IS NULL;
```

### 4.3 The polling & alert engine

```
Every hour:
  1. Query pnrs WHERE chart_prepared_at IS NULL AND travel_date >= CURRENT_DATE
  2. For each pnr (batch 20):
     - Call RapidAPI (backoff 1s, retry 2x, fallback provider)
     - Write to pnr_status_history
     - If status changed materially → trigger OneSignal push to owner
     - If chart prepared → lock outcome, mark final_status, trigger prediction scoring
  3. Respect rate limits: max 3 req/sec per provider
  4. Log provider health metrics for failover decisions
```

### 4.4 Rate limiting & fair use

- **Free tier:** 5 predictions/day per IP, 2 tracked PNRs
- **Pro tier (₹99/mo):** 100 predictions/day, 20 tracked PNRs, push alerts, historical train explorer
- **Hard cap everywhere:** 1000 req/day per user max, enforced at Redis layer, prevents scraper abuse

### 4.5 The public model card page (`/how-predictions-work`)

This is your trust moat. Publish:
- Feature list (full)
- Training dataset size + date range
- Held-out Brier score + AUC
- Calibration curve (visible chart)
- Last retrained date
- Known failure modes: "We are less accurate for trains with <100 historical observations"

Confirmtkt has none of this. Building this into the product from day 1 makes RailPulse the "honest one" in the category.

---

## 5. Legal & Compliance (Agent 11)

| Concern | Mitigation |
|---|---|
| **IRCTC ToS — scraping** | Do not scrape IRCTC directly. Use RapidAPI third-party wrappers (they are the liable party for their data sourcing). Document this clearly in the FAQ. |
| **"Not affiliated with IRCTC" disclaimer** | Prominent on homepage footer, in app store listing, in terms |
| **Trademark** | Don't use the IRCTC logo, name in domain, or IR colors. "RailPulse" is generic. |
| **DPDP Act** | PNR contains name/age on query, so PII. Don't store PNR→name mapping beyond 30 days. Hash PNRs for analytics. |
| **Prediction accuracy liability** | Terms: "Predictions are probabilistic estimates based on historical data. We make no guarantee of confirmation. Always have a backup plan." |
| **Paid tier refund policy** | Standard 7-day refund to avoid UPI chargebacks |
| **Account termination** | Right to revoke for abuse (scraping, reverse-engineering, etc.) |

**You specifically don't do:**
- Store IRCTC usernames/passwords (never ask for them)
- Submit any form to IRCTC on behalf of user
- Offer any Tatkal "speed booking" feature
- Promise any specific outcome

---

## 6. Monetization & Unit Economics (Agent 18)

| Tier | Price | Features | Target |
|---|---|---|---|
| **Free** | ₹0 | 5 predictions/day, 2 PNR tracking, basic alerts | 95% of users |
| **Pro** | ₹99/mo or ₹799/yr | 100 predictions/day, 20 PNR tracking, push alerts, historical explorer, alt-train suggestions | Frequent travelers |
| **Pro Annual (early bird)** | ₹499/yr first 1000 users | Same as Pro | Launch-phase conversion push |

**Cost stack (monthly, at 10K MAU):**
- RapidAPI: ~₹2,000 (depending on plan + PNR polling volume)
- Hosting (Railway): ~₹800
- OneSignal: free tier
- Domain/misc: ~₹200
- **Total:** ~₹3,000/mo

**Break-even:** 30 Pro subscribers (~0.3% conversion at 10K MAU). Realistic.
**Profitable at:** 100 Pro subscribers (~1% conversion). Achievable with good UX + LinkedIn launch post.

---

## 7. RailPulse Build Plan (4 weekends)

### Weekend 1: Foundation + cold-start model
- **Sat:** Repo, FastAPI scaffold, PostgreSQL + TimescaleDB on Railway, schema migration, RapidAPI account setup
- **Sun morning:** `/predict` endpoint with stub model, `/track-pnr` endpoint with RapidAPI integration
- **Sun afternoon:** Load Kaggle railway dataset, train v0 logistic regression in Jupyter, save as .pkl, wire into FastAPI
- **Sun evening:** First end-to-end prediction working locally

### Weekend 2: Frontend + data collection loop
- **Sat:** Next.js frontend scaffold (reuse TrainPool component library), prediction form, PNR tracking UI
- **Sun morning:** PNR polling cron + status history writes
- **Sun afternoon:** User auth (magic link again), saved PNRs, basic dashboard
- **Sun evening:** Deploy to staging, test with your own real PNRs

### Weekend 3: ML v1 + calibration + model card
- **Sat morning:** Train LightGBM v1 on whatever data you've collected + Kaggle combined
- **Sat afternoon:** Isotonic calibration layer, backtest, eval metrics pipeline
- **Sat evening:** Public model card page with live metrics
- **Sun morning:** Push notifications via OneSignal
- **Sun afternoon:** Rate limiting + Pro tier gating
- **Sun evening:** Razorpay integration (copy from Maha Jyotish)

### Weekend 4: Polish, landing, launch
- **Sat morning:** Landing page (anti-slop-design skill, same aesthetic family as TrainPool)
- **Sat afternoon:** SEO (schema.org/TravelAction, OG tags, sitemap), privacy/terms
- **Sat evening:** Cross-promo banner in TrainPool linking to RailPulse
- **Sun morning:** LinkedIn launch post (leveraging 28K audience), r/indianrailways post, IndiaHackers post
- **Sun afternoon:** Monitor, respond to feedback
- **Sun evening:** Dashboard for yourself — daily active users, Pro conversions, model eval metrics

**Deliverable at end of W4:** Live at railpulse.app, model v1 deployed, first 100 paying users target over next 4 weeks.

---

---

# PART III: CROSS-PRODUCT CONCERNS

## 8. Unified Brand & Landing (Agent 15)

**Suite name:** "RailPulse Suite" or keep them separate with reciprocal links
**Aesthetic:** Indian Railways-inspired but not using their trademarks. Think: deep forest green + warm ivory + signal-orange accent. Film grain, real train photography from Unsplash, no emojis, no AI sparkles (per your anti-slop-design skill).
**Typography pairing:** Something with weight — e.g., Fraunces (display) + Inter (body), or GT Sectra + Söhne.

## 9. Shared Infrastructure
- One Supabase project with two schemas (`trainpool`, `railpulse`)
- Shared magic-link auth so a user who signs up on one can use the other
- Shared domain strategy: `trainpool.in` and `railpulse.in` (or `.app`) with a tiny `about.railpulse.in/suite` landing that explains the two products as a suite

## 10. Launch Sequence (Agent 14)

```
Week 0:  Build TrainPool (2 weekends during build phase)
Week 2:  Soft launch TrainPool to your WhatsApp groups
Week 3:  LinkedIn post #1: "I built TrainPool because my group bookings are chaos"
Week 4–7: Build RailPulse (4 weekends)
Week 7:  Soft launch RailPulse to TrainPool users (cross-promo)
Week 8:  LinkedIn post #2: "I built an honest PNR prediction tool — here's the model card"
Week 9:  r/indianrailways + r/india + IndiaHackers + HackerNews Show-HN
Week 10: Product Hunt launch
Week 12: First paid conversions hit
```

## 11. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| RapidAPI provider shuts down | Medium | High | Use 2 providers, abstract behind adapter interface |
| IRCTC changes PNR format | Low | High | Retry-and-fallback, accept graceful degradation |
| ML model drifts | Medium | Medium | Weekly eval, auto-alert on calibration drift > 5% |
| DPDP audit / complaint | Low | High | Privacy by design, prominent policy, responsive to DPDP requests |
| Confirmtkt copies your model card approach | Medium | Low | Your moat is UX + honesty, not the feature itself |
| Trademark complaint from IRCTC | Low | Medium | Clear disclaimers, don't use IRCTC marks, have a takedown response ready |
| Low Pro conversion | Medium | Medium | Adjust pricing, add more free features, try one-time purchase option |
| You get bored/busy with EY work | High | High | Ship TrainPool in 2 weekends — even if RailPulse takes 6 months, TrainPool is a working product |

## 12. Decision Record (KDR)

```
════════════════════════════════════════════════════════════════
KDR — IRCTC Companion Suite — v1.0 — April 2026

PRODUCTS: 2 (TrainPool, RailPulse) — companion strategy, shared auth
SEQUENCE: TrainPool first (2 weekends), then RailPulse (4 weekends)

DECISIONS MADE:
1. NO booking automation of any kind — legal risk under Railways Act
2. TrainPool = coordination tool only, zero IRCTC integration
3. RailPulse = read-only intelligence via RapidAPI, not direct scraping
4. TrainPool stack: Next.js 15 + Supabase + Vercel
5. RailPulse stack: FastAPI + Postgres/TimescaleDB + Next.js + Railway
6. Shared magic-link auth across both products
7. ML: v0 logistic regression cold-start, v1 LightGBM with isotonic calibration
8. Privacy: ID proofs encrypted per-trip, auto-delete after travel date
9. Pricing: TrainPool free forever, RailPulse freemium ₹99/mo
10. Data moat strategy: build own historical waitlist dataset from day 1
11. Public model card as trust differentiator vs Confirmtkt
12. No LLM/chatbot — the ML model IS the product
13. Launch via LinkedIn 28K + Reddit + Show-HN, no paid ads in v1
14. Domain: trainpool.in + railpulse.app (verify availability)

OPEN ITEMS:
1. Verify RapidAPI IRCTC1 pricing at your expected volume
2. Check trainpool.in + railpulse.app domain availability
3. Review Kaggle for Indian Railways historical datasets
4. Decide: self-host PostHog or use Plausible for analytics
5. OneSignal free tier limits at your target scale

NEXT STEPS:
1. Start TrainPool Weekend 1 — set up Next.js + Supabase scaffold
2. Register domains
3. Create RapidAPI account (for RailPulse, not needed yet)
4. Draft LinkedIn announcement copy for end of Weekend 2
════════════════════════════════════════════════════════════════
```
