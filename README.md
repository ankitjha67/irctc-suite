# IRCTC Companion Suite

> Two legitimate, shippable products that solve real Indian Railways pain without touching booking automation.

| Product | One-liner | Stack | Status |
|---|---|---|---|
| [**TrainPool**](./trainpool) | Coordinate group passenger details without WhatsApp chaos | Next.js 15 + Supabase | Scaffold |
| [**RailPulse**](./railpulse) | Honest PNR confirmation probability with a public model card | FastAPI + LightGBM + TimescaleDB | Scaffold |

## What this is NOT

This suite explicitly does **not** automate IRCTC booking in any way. Tatkal booking automation is a criminal matter under Section 143 of the Railways Act, and nothing in this repo touches that line.

- TrainPool is a pure coordination tool — it never talks to IRCTC
- RailPulse consumes public PNR data via third-party RapidAPI wrappers (read-only)
- Neither product handles IRCTC credentials, submits forms, or solves captchas

## The plan

See [`PLAN.md`](./PLAN.md) for the full product-architect framework output:
- Problem statements and user stories
- Technical architecture per product
- ML approach for RailPulse (feature engineering, calibration, model card)
- Security, DPDP compliance, legal posture
- Monetization and unit economics
- 6-weekend build plan (2 for TrainPool, 4 for RailPulse)
- Risk matrix and KDR

## Getting started

```bash
# TrainPool
cd trainpool
cp .env.example .env.local
npm install
npm run dev

# RailPulse
cd ../railpulse
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

## Build sequence

1. **Weekends 1–2:** Ship TrainPool (simpler, faster feedback, seeds the userbase)
2. **Weekends 3–6:** Ship RailPulse v0 (cold-start logistic regression → LightGBM v1)
3. **Ongoing:** Collect labeled waitlist data in production, retrain monthly, publish calibration updates to the public model card

## Author

Ankit Jha — Manager, Financial Services Risk Management @ EY | Open-source builder
