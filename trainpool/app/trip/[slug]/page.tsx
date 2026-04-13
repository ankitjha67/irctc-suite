import Link from "next/link";
import { notFound } from "next/navigation";
import { format, formatDistanceToNow, isPast } from "date-fns";
import { createServiceClient } from "@/lib/supabase/server";
import { PassengerForm } from "./form";

type Params = { slug: string };

export default async function PublicTripPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { slug } = await params;

  // Use service client: this page is public, but we only expose non-PII fields
  const supabase = createServiceClient();
  const { data: trip } = await supabase
    .from("trips")
    .select("id, slug, name, train_number, travel_date, deadline, expected_count, id_proof_required, status")
    .eq("slug", slug)
    .maybeSingle();

  if (!trip) notFound();

  // Count how many passengers have joined (public, no PII)
  const { count: filledCount } = await supabase
    .from("passengers")
    .select("*", { count: "exact", head: true })
    .eq("trip_id", trip.id);

  const deadlinePassed = isPast(new Date(trip.deadline));
  const tripLocked = trip.status !== "active" || deadlinePassed;
  const slotsRemaining = trip.expected_count
    ? Math.max(0, trip.expected_count - (filledCount ?? 0))
    : null;
  const tripFull = slotsRemaining === 0;

  return (
    <main className="min-h-screen">
      <nav className="border-b border-ink-200 bg-ink-50/80 backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
          <Link href="/" className="font-display text-xl font-semibold text-ink-800">
            TrainPool
          </Link>
          <span className="text-xs text-ink-400">Not affiliated with IRCTC</span>
        </div>
      </nav>

      <div className="mx-auto max-w-xl px-6 py-10">
        {/* Trip context */}
        <header>
          <p className="text-xs font-medium uppercase tracking-wider text-forest-700">Group trip</p>
          <h1 className="mt-2 font-display text-3xl font-semibold text-ink-800">{trip.name}</h1>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-600">
            {trip.train_number && <span>Train {trip.train_number}</span>}
            <span>Travel {format(new Date(trip.travel_date), "d MMM yyyy")}</span>
          </div>
          <p className="mt-3 text-sm text-ink-500">
            {filledCount ?? 0}
            {trip.expected_count ? ` of ${trip.expected_count}` : ""} passenger
            {filledCount === 1 ? "" : "s"} have filled their details.
          </p>
        </header>

        {/* Deadline banner */}
        {tripLocked ? (
          <div className="mt-6 rounded-md border border-signal-200 bg-signal-50 p-4">
            <p className="font-medium text-signal-800">This trip is locked</p>
            <p className="mt-1 text-sm text-signal-700">
              {deadlinePassed
                ? `The deadline passed ${formatDistanceToNow(new Date(trip.deadline), {
                    addSuffix: true,
                  })}.`
                : `The organizer has locked this trip.`}{" "}
              Contact the organizer if you still need to add your details.
            </p>
          </div>
        ) : tripFull ? (
          <div className="mt-6 rounded-md border border-signal-200 bg-signal-50 p-4">
            <p className="font-medium text-signal-800">This trip is full</p>
            <p className="mt-1 text-sm text-signal-700">
              All {trip.expected_count} passenger slots have been filled. Contact the organizer if
              you believe this is a mistake.
            </p>
          </div>
        ) : (
          <div className="mt-6 rounded-md border border-forest-200 bg-forest-50 p-4">
            <p className="text-sm text-forest-800">
              <span className="font-medium">Deadline:</span>{" "}
              {format(new Date(trip.deadline), "d MMM, h:mm a")} (
              {formatDistanceToNow(new Date(trip.deadline), { addSuffix: true })})
            </p>
          </div>
        )}

        {/* Form */}
        {!tripLocked && !tripFull && (
          <div className="mt-8">
            <h2 className="font-display text-lg font-semibold text-ink-800">Your details</h2>
            <p className="mt-1 text-sm text-ink-600">
              Fill in as they appear on your ID. The organizer will use these to book on IRCTC.
            </p>

            <div className="mt-4">
              <PassengerForm slug={slug} idProofRequired={trip.id_proof_required} />
            </div>
          </div>
        )}

        {/* Privacy footnote */}
        <footer className="mt-12 border-t border-ink-200 pt-6 text-xs text-ink-500">
          <p>
            Your details are visible only to the trip organizer. ID numbers are encrypted. Everything
            auto-deletes 24 hours after the travel date. TrainPool never talks to IRCTC directly.
          </p>
        </footer>
      </div>
    </main>
  );
}
