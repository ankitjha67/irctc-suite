import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { format, formatDistanceToNow, isPast } from "date-fns";
import { createClient } from "@/lib/supabase/server";
import { TripDashboard } from "./dashboard";

type Params = { slug: string };

export default async function OrganizerTripPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { slug } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  // Fetch trip + verify ownership
  const { data: trip } = await supabase
    .from("trips")
    .select(
      "id, slug, name, train_number, travel_date, deadline, expected_count, id_proof_required, status, created_at"
    )
    .eq("slug", slug)
    .eq("organizer_id", user.id)
    .single();

  if (!trip) notFound();

  // Fetch initial passengers (realtime subscription in the client component will keep this fresh)
  const { data: passengers } = await supabase
    .from("passengers")
    .select("id, full_name, age, gender, berth_preference, id_type, id_number_hint, submitted_at")
    .eq("trip_id", trip.id)
    .order("submitted_at", { ascending: true });

  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  const shareUrl = `${appUrl}/trip/${trip.slug}`;

  const deadlinePassed = isPast(new Date(trip.deadline));
  const deadlineRelative = formatDistanceToNow(new Date(trip.deadline), { addSuffix: true });

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <Link href="/dashboard" className="text-sm text-ink-600 hover:text-ink-800">
        ← All trips
      </Link>

      {/* Header */}
      <header className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-ink-800">{trip.name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-600">
            {trip.train_number && (
              <span>
                <span className="font-medium text-ink-700">Train </span>
                {trip.train_number}
              </span>
            )}
            <span>
              <span className="font-medium text-ink-700">Travel </span>
              {format(new Date(trip.travel_date), "d MMM yyyy")}
            </span>
            <span>
              <span className="font-medium text-ink-700">Deadline </span>
              {deadlinePassed ? (
                <span className="text-signal-700">passed {deadlineRelative}</span>
              ) : (
                <span>{deadlineRelative}</span>
              )}
            </span>
          </div>
        </div>
      </header>

      <TripDashboard
        trip={trip}
        initialPassengers={passengers ?? []}
        shareUrl={shareUrl}
      />
    </main>
  );
}
