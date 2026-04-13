"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type BlockData = {
  tsv: string;
  pretty: string;
  row_count: number;
  warnings: string[];
};

export function GenerateBlockModal({
  open,
  onClose,
  tripSlug,
}: {
  open: boolean;
  onClose: () => void;
  tripSlug: string;
}) {
  const [loading, setLoading] = useState(false);
  const [block, setBlock] = useState<BlockData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) {
      // Reset state when modal closes so next open fetches fresh
      setBlock(null);
      setError(null);
      setCopied(false);
      return;
    }

    async function fetchBlock() {
      setLoading(true);
      setError(null);

      try {
        // Get the access token so the API route can verify the organizer
        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) {
          setError("Your session expired. Please sign in again.");
          setLoading(false);
          return;
        }

        const res = await fetch(`/api/trips/${tripSlug}/generate-block`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({ error: "Failed to generate block" }));
          setError(data.error ?? "Something went wrong");
          setLoading(false);
          return;
        }

        const data = (await res.json()) as BlockData;
        setBlock(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchBlock();
  }, [open, tripSlug]);

  async function handleCopy() {
    if (!block) return;
    try {
      await navigator.clipboard.writeText(block.tsv);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard. Select the text below and copy manually.");
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/60 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="flex items-start justify-between border-b border-ink-200 px-6 py-4">
          <div>
            <h2 id="modal-title" className="font-display text-xl font-semibold text-ink-800">
              Passenger block
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              Copy this and paste it into the first field of IRCTC&apos;s passenger details form.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5">
          {loading && <p className="text-sm text-ink-500">Generating...</p>}

          {error && (
            <div className="rounded-md bg-signal-50 px-4 py-3 text-sm text-signal-700">{error}</div>
          )}

          {block && (
            <>
              {block.warnings.length > 0 && (
                <div className="mb-4 rounded-md border border-signal-200 bg-signal-50 px-4 py-3">
                  <p className="text-sm font-medium text-signal-800">Warnings</p>
                  <ul className="mt-1 list-disc pl-5 text-sm text-signal-700">
                    {block.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm text-ink-600">
                  {block.row_count} passenger{block.row_count === 1 ? "" : "s"}
                </span>
                <button type="button" onClick={handleCopy} className="btn-primary">
                  {copied ? "Copied!" : "Copy to clipboard"}
                </button>
              </div>

              <div className="rounded-md border border-ink-200 bg-ink-900 p-4">
                <pre className="overflow-x-auto whitespace-pre font-mono text-xs text-ink-50">
                  {block.pretty}
                </pre>
              </div>

              <div className="mt-4 rounded-md border border-forest-200 bg-forest-50 px-4 py-3 text-sm text-forest-800">
                <p className="font-medium">Next: paste into IRCTC</p>
                <ol className="mt-2 list-decimal pl-5 text-forest-700">
                  <li>Open the IRCTC booking page and reach the passenger details step</li>
                  <li>Click into the first name field</li>
                  <li>Paste (Ctrl+V or Cmd+V) — the fields fill in automatically</li>
                  <li>Double-check everything before submitting</li>
                </ol>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
