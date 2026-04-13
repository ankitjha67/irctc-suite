\## Summary



Weekend 1 of the TrainPool build plan — ships the full coordination loop end to end.



\## What works after this PR



\- \*\*Magic-link auth\*\* via Supabase: sign in with email, no passwords

\- \*\*Landing page\*\* with hero + how-it-works + privacy positioning

\- \*\*Organizer dashboard\*\* listing all trips with status badges

\- \*\*Create trip form\*\* with full validation (date guards, train number format, deadline vs travel date, count caps)

\- \*\*Share card\*\* with copy-link and WhatsApp deep-link

\- \*\*Realtime passenger list\*\* that updates live as members submit

\- \*\*Generate Block modal\*\* that fetches the TSV via the existing API route and copies to clipboard

\- \*\*Public member form\*\* mobile-first, with localStorage profile autofill (names only — ID numbers never cached)

\- \*\*Three edge-case states\*\* on the public page: deadline passed, trip locked, trip full



\## Commits in this PR



1\. `foundation` — Next.js 15 + Tailwind design tokens + Supabase SSR clients + session-refresh middleware

2\. `landing + auth` — public homepage, magic-link login, callback handler

3\. `dashboard + trip creation` — organizer area, trip list, create form, live passenger view, generate block

4\. `member form` — public `/trip/\[slug]` page with validation and privacy-respecting autofill



\## Deployment prerequisites



Before merging, make sure the Supabase project has:



\- \[ ] The schema migration from `trainpool/supabase/migrations/0001\_init.sql` applied

\- \[ ] Email auth enabled (Authentication → Providers → Email → Enable)

\- \[ ] The site URL set to the Vercel deployment URL (Authentication → URL Configuration)

\- \[ ] Realtime enabled on the `passengers` table (Database → Replication → enable for `passengers`)



And the Vercel project has these env vars:



\- `NEXT\_PUBLIC\_SUPABASE\_URL`

\- `NEXT\_PUBLIC\_SUPABASE\_ANON\_KEY`

\- `SUPABASE\_SERVICE\_ROLE\_KEY`

\- `TRIP\_ENCRYPTION\_SECRET` (32+ random chars)

\- `NEXT\_PUBLIC\_APP\_URL` (the Vercel URL)



\## Testing checklist



\- \[ ] Sign in via magic link works end-to-end

\- \[ ] Create a test trip, copy the share link

\- \[ ] In an incognito window, open the link and submit passenger details

\- \[ ] Verify the organizer dashboard updates live without refresh

\- \[ ] Submit 2–3 more passengers, generate the block, verify the TSV format

\- \[ ] Try pasting into a local text editor — confirm tab-separated columns

\- \[ ] Test deadline expiry by setting a past deadline manually in Supabase



\## Out of scope (Weekend 2)



\- Email reminders via Resend when deadline approaches

\- Auto-delete cron on Supabase

\- Anti-slop-design landing page polish (real photography, film grain)

\- Privacy policy and terms pages

\- Supabase pg\_cron job for `auto\_delete\_at`



\## Not doing, ever



\- No IRCTC login handling

\- No form submission to IRCTC

\- No Tatkal booking automation

