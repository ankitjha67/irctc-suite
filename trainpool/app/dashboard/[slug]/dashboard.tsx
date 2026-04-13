"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import { createClient } from "@/lib/supabase/client";
import { GenerateBlockModal } from "./generate-block-modal";

type Passenger = {
  id: string;
  full_name: string;
  age: number;
  gender: "M" | "F" | "T";
  berth_preference: string | null;
  id_type: string | null;
  id_number_hint: string | null;
  submitted_at: string;
};

type Trip = {
  id: string;
  slug: string;
  name: string;
  expected_count: number | null;
  id_proof_required: boolean;
  status: string;
};

export function TripDashboard({
  trip,
  initialPassengers,
  shareUrl,
}: {
  trip: Trip;
  initialPassengers: Passenger[];
  shareUrl: string;
}) {
  const [passengers, setPassengers] = useState<Passenger[]>(initialPassengers);
  const [copied, setCopied] = useState<"link" | "message" | null>(null);
  const [blockOpen, setBlockOpen] = useState(false);

  // Realtime subscription — whenever a new passenger joins, update the list
  useEffect(() => {
    const supabase = createClient();

    const channel = supabase
      .channel(`trip-${trip.id}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "passengers",
          filter: `trip_id=eq.${trip.id}`,
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            setPassengers((prev) => [...prev, payload.new as Passenger]);
          } else if (payload.eventType === "UPDATE") {
            setPassengers((prev) =>
              prev.map((p) => (p.id === (payload.new as Passenger).id ? (payload.new as Passenger) : p))
            );
          } else if (payload.eventType === "DELETE") {
            setPassengers((prev) => prev.filter((p) => p.id !== (payload.old as Passenger).id));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [trip.id]);

  async function copyToClipboard(text: string, kind: "link" | "message") {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // Ignore — clipboard API fails in some sandboxed contexts
    }
  }

  const whatsappMessage = `I'm organising "${trip.name}" on TrainPool. Please fill in your passenger details at:\n${shareUrl}\n\nIt takes 60 seconds on your phone.`;
  const whatsappHref = `https://wa.me/?text=${encodeURIComponent(whatsappMessage)}`;

  const filledCount = passengers.length;
  const expectedCount = trip.expected_count ?? 0;
  const allFilled = expectedCount > 0 && filledCount >= expectedCount;

  return (
    <>
      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        {/* Share card */}
        <section className="card lg:col-span-1">
          <h2 className="font-display text-lg font-semibold text-ink-800">Share with your group</h2>
          <p className="mt-1 text-sm text-ink-600">
            Anyone with this link can add their details until the deadline.
          </p>

          <div className="mt-4 space-y-3">
            <div>
              <label className="label">Link</label>
              <div className="flex gap-2">
                <input type="text" readOnly value={shareUrl} className="input font-mono text-xs" />
                <button
                  type="button"
                  onClick={() => copyToClipboard(shareUrl, "link")}
                  className="btn-secondary whitespace-nowrap"
                >
                  {copied === "link" ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => copyToClipboard(whatsappMessage, "message")}
                className="btn-secondary flex-1"
              >
                {copied === "message" ? "Message copied!" : "Copy WhatsApp message"}
              </button>
              <a
                href={whatsappHref}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary flex-1 text-center"
              >
                Open WhatsApp
              </a>
            </div>
          </div>
        </section>

        {/* Passenger list */}
        <section className="card lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-ink-800">
              Passengers ({filledCount}
              {expectedCount > 0 ? ` / ${expectedCount}` : ""})
            </h2>
            {allFilled && (
              <span className="rounded-full bg-forest-100 px-2.5 py-0.5 text-xs font-medium text-forest-800">
                All filled
              </span>
            )}
          </div>

          {passengers.length === 0 ? (
            <div className="mt-6 rounded-md border border-dashed border-ink-200 bg-ink-50 p-8 text-center">
              <p className="text-sm text-ink-600">
                No one has filled in their details yet. Share the link above with your group.
              </p>
              <p className="mt-2 text-xs text-ink-400">This list updates in real-time as people join.</p>
            </div>
          ) : (
            <ul className="mt-4 divide-y divide-ink-100">
              {passengers.map((p, idx) => (
                <li key={p.id} className="flex items-center justify-between py-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-ink-400">#{idx + 1}</span>
                      <span className="font-medium text-ink-800">{p.full_name}</span>
                    </div>
                    <div className="mt-0.5 text-xs text-ink-500">
                      {p.age}y · {p.gender === "M" ? "Male" : p.gender === "F" ? "Female" : "Trans"}
                      {p.berth_preference && ` · ${p.berth_preference}`}
                      {p.id_type && p.id_number_hint && ` · ${p.id_type} ${p.id_number_hint}`}
                    </div>
                  </div>
                  <time className="text-xs text-ink-400">
                    {format(new Date(p.submitted_at), "h:mm a")}
                  </time>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-6 flex items-center justify-between border-t border-ink-200 pt-6">
            <p className="text-xs text-ink-500">
              When ready, generate a paste-ready block to paste into IRCTC&apos;s passenger form.
            </p>
            <button
              type="button"
              onClick={() => setBlockOpen(true)}
              disabled={filledCount === 0}
              className="btn-signal"
            >
              Generate block
            </button>
          </div>
        </section>
      </div>

      <GenerateBlockModal
        open={blockOpen}
        onClose={() => setBlockOpen(false)}
        tripSlug={trip.slug}
      />
    </>
  );
}
