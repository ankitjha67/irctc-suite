# Deploying RailPulse to Railway

RailPulse ships as a containerized FastAPI service. We deploy it on
[Railway](https://railway.app) because Railway natively supports monorepo
subdirectory roots, has a generous free tier ($5/month credit which comfortably
covers our first ~10K requests), and deploys automatically on every push to
`main`.

> **Not deploying to:** Fly.io, Render, AWS. The operational overhead
> isn't worth it for a v0 API service.

---

## 1. Prerequisites

- A Railway account connected to the `ankitjha67/irctc-suite` GitHub repo.
- The RailPulse migration (`railpulse/supabase/migrations/0001_railpulse_init.sql`)
  run once against the shared Supabase project (the same project that hosts
  TrainPool).
- A [RapidAPI](https://rapidapi.com) account subscribed to **both**:
  - `irctc1.p.rapidapi.com` (primary)
  - `irctc-indian-railway-pnr-status.p.rapidapi.com` (fallback)

## 2. Run the migration

From the Supabase SQL editor for project `abhfkspbjgxnorbeeqbo`, paste and
execute the contents of `railpulse/supabase/migrations/0001_railpulse_init.sql`.
After it completes you should see a new `railpulse` schema with these tables:

- `railpulse.trains`
- `railpulse.pnrs`
- `railpulse.pnr_status_history`
- `railpulse.predictions`
- `railpulse.api_usage`
- `railpulse.model_eval_snapshots`

The migration is idempotent — running it again is a no-op.

## 3. Create the Railway project

1. In Railway, click **New Project → Deploy from GitHub repo**.
2. Select `ankitjha67/irctc-suite`.
3. When prompted, set **Root Directory** to `railpulse`. This is the same
   monorepo trick we use for TrainPool on Vercel — it tells Railway to treat
   the `railpulse/` subdirectory as the build context so it picks up our
   `Dockerfile`.
4. Railway auto-detects the `Dockerfile` and uses it. (If it tries to use
   Nixpacks instead, force the Dockerfile builder in Settings → Build.)

## 4. Set environment variables

Under **Variables**, add every variable from `.env.example`:

| Key | Value |
|-----|-------|
| `ENV` | `prod` |
| `SECRET_KEY` | generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | the Supabase **pooler** URL, format:<br>`postgresql+psycopg://postgres.abhfkspbjgxnorbeeqbo:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres` |
| `RAPIDAPI_KEY` | your RapidAPI key |
| `RAPIDAPI_PRIMARY_HOST` | `irctc1.p.rapidapi.com` |
| `RAPIDAPI_FALLBACK_HOST` | `irctc-indian-railway-pnr-status.p.rapidapi.com` |
| `FREE_PREDICTIONS_PER_DAY` | `5` |
| `FREE_TRACKED_PNRS` | `2` |
| `PRO_PREDICTIONS_PER_DAY` | `100` |
| `PRO_TRACKED_PNRS` | `20` |
| `MODEL_PATH` | `models/v0_logistic.pkl` |
| `MODEL_VERSION` | `v0-heuristic` |

> **Pooler vs direct connection:** Start with the pooler URL shown above. If
> you hit "prepared statement does not exist" errors from asyncpg against the
> transaction-mode pooler, switch to Supabase's **session-mode** pooler or the
> direct `db.<ref>.supabase.co:5432` URL.

## 5. Deploy

Railway builds the container on first deploy and redeploys on every push to
`main` that touches `railpulse/**`. Watch the build logs until the healthcheck
at `GET /health` turns green.

## 6. (Optional) Attach a custom domain

1. In Railway → Settings → Networking → **Custom Domain**, add e.g. `api.railpulse.in`.
2. Add the `CNAME` record Railway shows you at your DNS provider.
3. Railway provisions TLS automatically via Let's Encrypt.

## 7. Verify the deploy

```bash
# Replace with your Railway-issued URL or custom domain
BASE=https://railpulse-production.up.railway.app

# Liveness
curl $BASE/health

# Predict
curl -X POST $BASE/v1/predict \
  -H 'Content-Type: application/json' \
  -d '{
    "train_number": "12951",
    "travel_date": "2026-05-01",
    "source_station": "BCT",
    "dest_station": "NDLS",
    "ticket_class": "3A",
    "quota": "GN",
    "current_wl_position": 12
  }'

# Model card
curl $BASE/v1/model-card

# Swagger UI
open $BASE/docs
```

## 8. Known operational caveats

- **Rate limits are per IP hash.** A shared corporate NAT will see its users
  collectively counted as one subject. Acceptable for v0.
- **No Redis.** Rate limit state lives in `railpulse.api_usage`. If the row
  churn becomes a problem, swap for Redis (add a Railway Redis plugin and
  wire it up in `app/api/rate_limit.py`).
- **Supabase free tier** has a 500MB database limit. At our volume that's
  years of headroom, but watch the `pnr_status_history` table — it's the
  biggest growth driver. Add a cron to prune rows older than 90 days once
  we have real traffic.
- **RapidAPI quotas.** Free tier of IRCTC1 is ~100 requests/day. Upgrade to
  the basic paid plan (~$10/month) before launch.
