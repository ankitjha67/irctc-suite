"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError(null);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithOtp({
      email: email.trim(),
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (authError) {
      setError(authError.message);
      setStatus("error");
      return;
    }

    setStatus("sent");
  }

  return (
    <main className="min-h-screen">
      <nav className="border-b border-ink-200">
        <div className="mx-auto max-w-6xl px-6 py-5">
          <Link href="/" className="font-display text-xl font-semibold text-ink-800">
            TrainPool
          </Link>
        </div>
      </nav>

      <div className="mx-auto max-w-md px-6 py-20">
        <h1 className="font-display text-3xl font-semibold text-ink-800">Sign in</h1>
        <p className="mt-3 text-ink-600">
          We&apos;ll email you a magic link. No passwords, no hassle.
        </p>

        {status === "sent" ? (
          <div className="mt-8 card border-forest-200 bg-forest-50">
            <p className="font-medium text-forest-800">Check your email</p>
            <p className="mt-2 text-sm text-forest-700">
              We sent a sign-in link to <span className="font-medium">{email}</span>. Tap it to continue.
            </p>
            <button
              type="button"
              onClick={() => {
                setStatus("idle");
                setEmail("");
              }}
              className="mt-4 text-sm text-forest-700 underline hover:text-forest-800"
            >
              Use a different email
            </button>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                autoFocus
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
              />
            </div>

            {error && (
              <p className="rounded-md bg-signal-50 px-3 py-2 text-sm text-signal-700">{error}</p>
            )}

            <button
              type="submit"
              disabled={status === "sending" || !email.trim()}
              className="btn-primary w-full"
            >
              {status === "sending" ? "Sending..." : "Send magic link"}
            </button>
          </form>
        )}

        <p className="mt-8 text-xs text-ink-400">
          By signing in you agree that TrainPool is an independent tool not affiliated with IRCTC.
          We never handle your IRCTC login or submit bookings on your behalf.
        </p>
      </div>
    </main>
  );
}
