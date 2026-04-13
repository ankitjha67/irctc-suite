## Summary

Initial scaffold for the IRCTC Companion Suite monorepo. Two products:

- **TrainPool** — coordinate group passenger details without WhatsApp chaos (Next.js 15 + Supabase)
- **RailPulse** — honest PNR confirmation probability with a public model card (FastAPI + LightGBM + TimescaleDB)

## What's in this PR

### `PLAN.md` — the full product-architect plan
Follows the `product-architect` framework (agents 02/03/04/06/09/11/14/18/29). Covers problem statements, user stories with acceptance criteria, technical architecture, data models, ML approach, security and DPDP compliance, monetization, the six-weekend build plan, risk matrix, and a closing decision record.

### `trainpool/` — Next.js + Supabase scaffold
- `lib/encryption.ts` — per-trip AES-256-GCM with HKDF key derivation. Compromise of one trip's key never cascades.
- `lib/paste-block.ts` — IRCTC-compatible TSV generator. Server-side, on-demand decryption. Never persisted as a derived artifact.
- `app/api/trips/[slug]/passengers/route.ts` — public passenger form endpoint with edit-token HttpOnly cookies. Members don't need accounts.
- `app/api/trips/[slug]/generate-block/route.ts` — organizer-only block generator with auth + ownership checks.
- `supabase/migrations/0001_init.sql` — schema with RLS policies + auto-delete hooks.

### `railpulse/` — FastAPI + LightGBM scaffold
- `app/main.py` — FastAPI entry with `/v1/predict`, `/v1/pnr/track`, `/v1/model-card`.
- `app/ml/features.py` — feature engineering shared between training and inference (no train/serve skew).
- `app/ml/predict.py` — calibrated prediction wrapper with confidence intervals and a cold-start fallback.
- `app/ml/train_v0.py` — runnable training pipeline: logistic regression + isotonic calibration, Brier + AUC reporting, calibration curve export.
- `app/data/rapidapi_client.py` — dual-provider adapter (IRCTC1 primary, fallback) with tenacity retries and automatic failover.
- `app/db/schema.sql` — PostgreSQL + TimescaleDB hypertable for WL movement, plus predictions log and model eval snapshots.

## What this suite explicitly does NOT do

- No IRCTC login or credential handling
- No form submission or booking automation
- No Tatkal speed-booking features
- No captcha solving

This is the legal-by-design stance. Section 143 of the Railways Act treats ticket procurement automation as a criminal matter, so we stay firmly on the coordination + read-only intelligence side of the line.

## Testing checklist (for follow-up PRs)

- [ ] TrainPool: create trip → add 3 passengers → generate block → verify TSV round-trips into IRCTC form
- [ ] TrainPool: encryption round-trip unit test (encrypt → decrypt returns original)
- [ ] TrainPool: deadline lock rejects submissions past deadline
- [ ] TrainPool: auto-delete cron removes expired trips
- [ ] RailPulse: v0 training run produces a valid calibration curve on Kaggle dataset
- [ ] RailPulse: `/v1/predict` returns a calibrated probability with the fallback heuristic when no model file is present
- [ ] RailPulse: dual-provider adapter fails over on primary 500
- [ ] RailPulse: `/v1/model-card` returns the expected eval JSON

## Open items before merge

1. Verify `trainpool.in` and `railpulse.app` domain availability
2. Confirm RapidAPI IRCTC1 response schema against `rapidapi_client.py` field mappings (marked with TODO comments)
3. Source a Kaggle Indian Railways PNR dataset for `data/raw/pnr_outcomes.csv`, or add a `data/synthetic.py` bootstrap generator
4. Decide: shared Supabase project with two schemas, or separate projects per product

## Next up

Weekend 1 TrainPool: trip creation flow + organizer magic-link auth + public passenger form + realtime dashboard + block generation + Vercel deploy.

---

🤖 *Plan and scaffold generated with [Claude](https://claude.ai) using the [product-architect](https://github.com/ankitjha67/product-architect) framework.*
