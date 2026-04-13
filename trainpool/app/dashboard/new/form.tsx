"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export function NewTripForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const fd = new FormData(e.currentTarget);
    const body = {
      name: String(fd.get("name") ?? "").trim(),
      train_number: String(fd.get("train_number") ?? "").trim() || null,
      travel_date: String(fd.get("travel_date") ?? ""),
      deadline: String(fd.get("deadline") ?? ""),
      expected_count: Number(fd.get("expected_count") ?? 0),
      id_proof_required: fd.get("id_proof_required") === "on",
    };

    const res = await fetch("/api/trips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: "Failed to create trip" }));
      setError(data.error ?? "Something went wrong");
      setSubmitting(false);
      return;
    }

    const { slug } = await res.json();
    router.push(`/dashboard/${slug}`);
  }

  // Default deadline: tomorrow at 9 PM (datetime-local format)
  const defaultDeadline = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(21, 0, 0, 0);
    return d.toISOString().slice(0, 16);
  })();

  return (
    <form onSubmit={onSubmit} className="card space-y-5">
      <div>
        <label htmlFor="name" className="label">
          Trip name
        </label>
        <input
          id="name"
          name="name"
          type="text"
          required
          maxLength={80}
          placeholder="e.g. Goa New Year trip"
          className="input"
        />
      </div>

      <div>
        <label htmlFor="train_number" className="label">
          Train number <span className="font-normal text-ink-400">(optional)</span>
        </label>
        <input
          id="train_number"
          name="train_number"
          type="text"
          maxLength={6}
          placeholder="e.g. 12951"
          className="input"
        />
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="travel_date" className="label">
            Travel date
          </label>
          <input
            id="travel_date"
            name="travel_date"
            type="date"
            required
            className="input"
            min={new Date().toISOString().slice(0, 10)}
          />
        </div>
        <div>
          <label htmlFor="expected_count" className="label">
            How many passengers?
          </label>
          <input
            id="expected_count"
            name="expected_count"
            type="number"
            required
            min={1}
            max={20}
            defaultValue={4}
            className="input"
          />
        </div>
      </div>

      <div>
        <label htmlFor="deadline" className="label">
          Deadline for members to fill
        </label>
        <input
          id="deadline"
          name="deadline"
          type="datetime-local"
          required
          defaultValue={defaultDeadline}
          className="input"
        />
        <p className="mt-1 text-xs text-ink-500">
          After this, the form locks. You can extend it later if needed.
        </p>
      </div>

      <div className="flex items-start gap-3 rounded-md border border-ink-200 bg-ink-50 p-4">
        <input
          id="id_proof_required"
          name="id_proof_required"
          type="checkbox"
          className="mt-0.5 h-4 w-4 rounded border-ink-300 text-forest-700 focus:ring-forest-500"
        />
        <div>
          <label htmlFor="id_proof_required" className="text-sm font-medium text-ink-800">
            Require ID proof
          </label>
          <p className="text-xs text-ink-500">
            IRCTC requires ID for trips longer than 500 km or for specific quotas. Members will be
            asked for ID type and number, encrypted per-trip.
          </p>
        </div>
      </div>

      {error && (
        <p className="rounded-md bg-signal-50 px-3 py-2 text-sm text-signal-700">{error}</p>
      )}

      <div className="flex items-center justify-end gap-3 border-t border-ink-200 pt-5">
        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? "Creating..." : "Create trip"}
        </button>
      </div>
    </form>
  );
}
