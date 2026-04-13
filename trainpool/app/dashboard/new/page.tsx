import Link from "next/link";
import { NewTripForm } from "./form";

export default function NewTripPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <Link href="/dashboard" className="text-sm text-ink-600 hover:text-ink-800">
        ← Back to trips
      </Link>

      <h1 className="mt-6 font-display text-3xl font-semibold text-ink-800">Create a trip</h1>
      <p className="mt-2 text-ink-600">
        Set the basics. You can share the link with your group immediately after.
      </p>

      <div className="mt-8">
        <NewTripForm />
      </div>
    </main>
  );
}
