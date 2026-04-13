# TrainPool

> Coordinate group train bookings without chasing people on WhatsApp.

**One-line pitch:** Organizer creates a trip → shares a link → each member fills their own details on mobile → organizer gets a paste-ready passenger block for IRCTC.

**What it is NOT:** A booking bot. TrainPool never talks to IRCTC. It is a pure coordination tool.

## Stack
- Next.js 15 (App Router)
- Supabase (Postgres + Auth + Realtime)
- shadcn/ui + Tailwind
- Vercel (hosting)
- Resend (deadline emails)

## Setup

```bash
# 1. Clone and install
git clone <your-repo>
cd trainpool
npm install

# 2. Set env vars
cp .env.example .env.local
# Fill in:
#   NEXT_PUBLIC_SUPABASE_URL
#   NEXT_PUBLIC_SUPABASE_ANON_KEY
#   SUPABASE_SERVICE_ROLE_KEY
#   TRIP_ENCRYPTION_SECRET  (32+ random chars, used to derive per-trip keys)
#   RESEND_API_KEY

# 3. Run migrations on your Supabase project
#    Paste contents of supabase/migrations/0001_init.sql in Supabase SQL editor

# 4. Dev
npm run dev
```

## Core files
- `lib/encryption.ts` — per-trip AES-256-GCM for ID numbers
- `lib/paste-block.ts` — IRCTC paste-format generator
- `supabase/migrations/0001_init.sql` — schema with RLS
- `app/api/trips/route.ts` — create trip (auth required)
- `app/api/trips/[slug]/passengers/route.ts` — public passenger form endpoint
- `app/api/trips/[slug]/generate-block/route.ts` — organizer-only block generator
- `app/trip/[slug]/page.tsx` — public member form
- `app/dashboard/[slug]/page.tsx` — organizer dashboard

## Privacy promise
- ID numbers encrypted at rest with per-trip key
- Passenger data auto-deletes 24h after travel date
- Members do not create accounts — only organizers do
- No third-party analytics, no ad trackers
