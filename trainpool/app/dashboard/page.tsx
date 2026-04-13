import Link from "next/link";
import { format } from "date-fns";
import { createClient } from "@/lib/supabase/server";

export default async function DashboardHome() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { data: trips } = await supabase
    .from("trips")
    .select("slug, name, train_number, travel_date, deadline, expected_count, status, created_at")
    .eq("organizer_id", user!.id)
    .order("travel_date", { ascending: true });

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink-800">Your trips</h1>
          <p className="mt-1 text-ink-600">Coordinate passenger details for group bookings.</p>
        </div>
        <Link href="/dashboard/new" className="btn-primary">
          New trip
        </Link>
      </div>

      <div className="mt-10">
        {!trips || trips.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {trips.map((t) => (
              <Link
                key={t.slug}
                href={`/dashboard/${t.slug}`}
                className="card transition hover:border-forest-400 hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <h2 className="font-display text-lg font-semibold text-ink-800">{t.name}</h2>
                  <StatusBadge status={t.status} />
                </div>
                <dl className="mt-4 space-y-1 text-sm text-ink-600">
                  {t.train_number && (
                    <div>
                      <dt className="inline font-medium text-ink-700">Train: </dt>
                      <dd className="inline">{t.train_number}</dd>
                    </div>
                  )}
                  <div>
                    <dt className="inline font-medium text-ink-700">Travel: </dt>
                    <dd className="inline">{format(new Date(t.travel_date), "d MMM yyyy")}</dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-ink-700">Deadline: </dt>
                    <dd className="inline">
                      {format(new Date(t.deadline), "d MMM, h:mm a")}
                    </dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-ink-700">Expected: </dt>
                    <dd className="inline">{t.expected_count} passengers</dd>
                  </div>
                </dl>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="card text-center">
      <h3 className="font-display text-xl font-semibold text-ink-800">No trips yet</h3>
      <p className="mx-auto mt-2 max-w-md text-ink-600">
        Create your first trip to start collecting passenger details from your group.
      </p>
      <Link href="/dashboard/new" className="btn-primary mt-6 inline-flex">
        Create your first trip
      </Link>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-forest-100 text-forest-800",
    locked: "bg-ink-200 text-ink-700",
    booked: "bg-signal-100 text-signal-800",
    expired: "bg-ink-100 text-ink-500",
  };
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] ?? styles.expired
      }`}
    >
      {status}
    </span>
  );
}
