"use client";

import { useEffect, useState } from "react";

type FormState = {
  full_name: string;
  age: string;
  gender: "M" | "F" | "T" | "";
  berth_preference: string;
  id_type: string;
  id_number: string;
};

const EMPTY_STATE: FormState = {
  full_name: "",
  age: "",
  gender: "",
  berth_preference: "NP",
  id_type: "",
  id_number: "",
};

const STORAGE_KEY = "trainpool_profile_v1";

export function PassengerForm({
  slug,
  idProofRequired,
}: {
  slug: string;
  idProofRequired: boolean;
}) {
  const [form, setForm] = useState<FormState>(EMPTY_STATE);
  const [savePrompt, setSavePrompt] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Autofill from localStorage if a profile exists
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = JSON.parse(raw) as Partial<FormState>;
        setForm((f) => ({ ...f, ...saved }));
      }
    } catch {
      // localStorage might be disabled — that's fine
    }
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    // Client-side validation for a fast failure path
    if (!form.full_name.trim() || form.full_name.trim().length < 2) {
      setError("Full name is required");
      setSubmitting(false);
      return;
    }
    const age = Number(form.age);
    if (!Number.isInteger(age) || age < 1 || age > 120) {
      setError("Age must be a whole number between 1 and 120");
      setSubmitting(false);
      return;
    }
    if (!form.gender) {
      setError("Please select a gender");
      setSubmitting(false);
      return;
    }
    if (idProofRequired && (!form.id_type || !form.id_number.trim())) {
      setError("The organizer has required ID proof for this trip");
      setSubmitting(false);
      return;
    }

    const payload = {
      full_name: form.full_name.trim(),
      age,
      gender: form.gender,
      berth_preference: form.berth_preference || null,
      id_type: form.id_type || null,
      id_number: form.id_number.trim() || null,
    };

    const res = await fetch(`/api/trips/${slug}/passengers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({ error: "Submission failed" }));
      const detail = Array.isArray(data.details) ? data.details.join("; ") : "";
      setError(data.error + (detail ? ` — ${detail}` : ""));
      setSubmitting(false);
      return;
    }

    setSuccess(true);
    setSavePrompt(true);
    setSubmitting(false);
  }

  function saveProfile() {
    try {
      // Save only the name / age / gender / berth — NEVER save ID number locally
      const profile = {
        full_name: form.full_name,
        age: form.age,
        gender: form.gender,
        berth_preference: form.berth_preference,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
      setSavePrompt(false);
    } catch {
      setError("Could not save profile locally");
    }
  }

  if (success) {
    return (
      <div className="card border-forest-200 bg-forest-50 text-forest-900">
        <p className="font-display text-lg font-semibold">Thanks — you&apos;re in</p>
        <p className="mt-1 text-sm">The organizer will see your details on their dashboard.</p>

        {savePrompt && (
          <div className="mt-4 border-t border-forest-200 pt-4">
            <p className="text-sm">
              Save your name, age, gender, and berth preference on this device for next time? ID
              numbers are never saved.
            </p>
            <div className="mt-3 flex gap-2">
              <button type="button" onClick={saveProfile} className="btn-primary">
                Save profile
              </button>
              <button
                type="button"
                onClick={() => setSavePrompt(false)}
                className="btn-secondary"
              >
                No thanks
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="card space-y-5">
      <div>
        <label htmlFor="full_name" className="label">
          Full name (as on ID)
        </label>
        <input
          id="full_name"
          type="text"
          required
          maxLength={80}
          autoComplete="name"
          value={form.full_name}
          onChange={(e) => update("full_name", e.target.value)}
          className="input"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="age" className="label">
            Age
          </label>
          <input
            id="age"
            type="number"
            required
            min={1}
            max={120}
            value={form.age}
            onChange={(e) => update("age", e.target.value)}
            className="input"
          />
        </div>
        <div>
          <label htmlFor="gender" className="label">
            Gender
          </label>
          <select
            id="gender"
            required
            value={form.gender}
            onChange={(e) => update("gender", e.target.value as FormState["gender"])}
            className="input"
          >
            <option value="">Select</option>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="T">Trans</option>
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="berth" className="label">
          Berth preference
        </label>
        <select
          id="berth"
          value={form.berth_preference}
          onChange={(e) => update("berth_preference", e.target.value)}
          className="input"
        >
          <option value="NP">No preference</option>
          <option value="LB">Lower</option>
          <option value="MB">Middle</option>
          <option value="UB">Upper</option>
          <option value="SL">Side Lower</option>
          <option value="SU">Side Upper</option>
        </select>
      </div>

      <div className={idProofRequired ? "" : "rounded-md bg-ink-50 p-4"}>
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-ink-800">
            ID proof {idProofRequired ? "(required)" : "(optional)"}
          </span>
          {!idProofRequired && (
            <span className="text-xs text-ink-500">Skip if organizer didn&apos;t ask</span>
          )}
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <select
            value={form.id_type}
            onChange={(e) => update("id_type", e.target.value)}
            className="input"
            required={idProofRequired}
          >
            <option value="">ID type</option>
            <option value="AADHAAR">Aadhaar</option>
            <option value="PAN">PAN</option>
            <option value="DL">Driving Licence</option>
            <option value="PASSPORT">Passport</option>
            <option value="VOTER">Voter ID</option>
          </select>
          <input
            type="text"
            placeholder="ID number"
            value={form.id_number}
            onChange={(e) => update("id_number", e.target.value)}
            className="input"
            required={idProofRequired}
            maxLength={32}
            autoComplete="off"
          />
        </div>

        <p className="mt-2 text-xs text-ink-500">
          ID numbers are encrypted with a key unique to this trip and are never saved to your
          device.
        </p>
      </div>

      {error && (
        <p className="rounded-md bg-signal-50 px-3 py-2 text-sm text-signal-700">{error}</p>
      )}

      <button type="submit" disabled={submitting} className="btn-primary w-full">
        {submitting ? "Submitting..." : "Submit my details"}
      </button>
    </form>
  );
}
