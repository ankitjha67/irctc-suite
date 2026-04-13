import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="border-b border-ink-200 bg-ink-50/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <Link href="/" className="font-display text-xl font-semibold text-ink-800">
            TrainPool
          </Link>
          <div className="flex items-center gap-3">
            {user ? (
              <Link href="/dashboard" className="btn-primary">
                Dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className="text-sm font-medium text-ink-600 hover:text-ink-800">
                  Sign in
                </Link>
                <Link href="/login" className="btn-primary">
                  Create a trip
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <h1 className="font-display text-5xl font-semibold leading-tight text-ink-800 md:text-6xl">
          Group train booking,
          <br />
          <span className="text-forest-700">without the WhatsApp chaos.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-ink-600">
          Share one link. Everyone fills their own details on their phone. You get a paste-ready
          passenger block for IRCTC in one click.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link href="/login" className="btn-primary px-6 py-3 text-base">
            Create a trip — free
          </Link>
          <Link href="#how" className="btn-secondary px-6 py-3 text-base">
            How it works
          </Link>
        </div>
        <p className="mt-6 text-xs text-ink-400">
          Not affiliated with IRCTC. We never handle your login or submit bookings.
        </p>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-ink-200 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="font-display text-3xl font-semibold text-ink-800">How it works</h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            <Step
              n="1"
              title="Create a trip"
              body="Trip name, travel date, and how many people are coming. Takes 30 seconds."
            />
            <Step
              n="2"
              title="Share the link"
              body="Drop it in your WhatsApp group. Each person taps it, fills their own details on mobile."
            />
            <Step
              n="3"
              title="Paste into IRCTC"
              body="When everyone's done, tap Generate. You get a tab-separated block to paste into the IRCTC passenger form."
            />
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section className="border-t border-ink-200 bg-ink-50">
        <div className="mx-auto max-w-5xl px-6 py-20">
          <h2 className="font-display text-3xl font-semibold text-ink-800">
            Privacy is the point
          </h2>
          <ul className="mt-8 space-y-4 text-ink-700">
            <Bullet>ID proof numbers are encrypted at rest with a key unique to your trip</Bullet>
            <Bullet>Passenger data auto-deletes 24 hours after the travel date</Bullet>
            <Bullet>
              Members don&apos;t need to create an account — only the organizer signs in
            </Bullet>
            <Bullet>No third-party analytics, no ad trackers, no cookies for marketing</Bullet>
          </ul>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <p className="text-sm text-ink-500">
              Built by{" "}
              <a
                href="https://github.com/ankitjha67"
                className="text-forest-700 hover:underline"
              >
                Ankit Jha
              </a>
            </p>
            <p className="text-xs text-ink-400">
              TrainPool is an independent tool. Not affiliated with IRCTC or Indian Railways.
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div>
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-forest-100 font-display text-lg font-semibold text-forest-700">
        {n}
      </div>
      <h3 className="font-display text-xl font-semibold text-ink-800">{title}</h3>
      <p className="mt-2 text-ink-600">{body}</p>
    </div>
  );
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-2 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-forest-600" />
      <span>{children}</span>
    </li>
  );
}
