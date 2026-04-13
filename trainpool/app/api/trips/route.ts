import { NextRequest, NextResponse } from "next/server";
import { customAlphabet } from "nanoid";
import { createClient } from "@/lib/supabase/server";

// URL-safe slug alphabet — no confusable chars (no 0/O/1/l/I)
const nanoid = customAlphabet("23456789abcdefghijkmnpqrstuvwxyz", 6);

/**
 * POST /api/trips
 *
 * Creates a new trip for the authenticated organizer.
 * Returns the slug so the client can redirect to the organizer dashboard.
 */
export async function POST(req: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "Invalid request body" }, { status: 400 });
  }

  // Validation
  const errors: string[] = [];

  const name = typeof body.name === "string" ? body.name.trim() : "";
  if (!name || name.length < 2 || name.length > 80) {
    errors.push("Trip name must be 2–80 characters");
  }

  const trainNumber =
    typeof body.train_number === "string" && body.train_number.trim().length > 0
      ? body.train_number.trim()
      : null;
  if (trainNumber && !/^\d{4,6}$/.test(trainNumber)) {
    errors.push("Train number must be 4–6 digits");
  }

  const travelDate = new Date(body.travel_date);
  if (isNaN(travelDate.getTime())) {
    errors.push("Invalid travel date");
  }
  // Travel date must be today or future
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (travelDate < today) {
    errors.push("Travel date cannot be in the past");
  }

  const deadline = new Date(body.deadline);
  if (isNaN(deadline.getTime())) {
    errors.push("Invalid deadline");
  }
  if (deadline < new Date()) {
    errors.push("Deadline must be in the future");
  }
  if (deadline > travelDate) {
    // Deadline after travel date is nonsensical
    errors.push("Deadline must be before the travel date");
  }

  const expectedCount = Number(body.expected_count);
  if (!Number.isInteger(expectedCount) || expectedCount < 1 || expectedCount > 20) {
    errors.push("Expected count must be a whole number between 1 and 20");
  }

  const idProofRequired = Boolean(body.id_proof_required);

  if (errors.length > 0) {
    return NextResponse.json({ error: errors.join("; ") }, { status: 400 });
  }

  // Rate limit: max 20 trips per organizer per day (simple app-layer check)
  const dayAgo = new Date();
  dayAgo.setDate(dayAgo.getDate() - 1);
  const { count: recentCount } = await supabase
    .from("trips")
    .select("*", { count: "exact", head: true })
    .eq("organizer_id", user.id)
    .gte("created_at", dayAgo.toISOString());

  if ((recentCount ?? 0) >= 20) {
    return NextResponse.json(
      { error: "Daily trip creation limit reached (20/day). Try again tomorrow." },
      { status: 429 }
    );
  }

  // Generate slug with collision retry — 32-char alphabet, 6 chars = ~1B space
  let slug = "";
  for (let attempt = 0; attempt < 5; attempt++) {
    const candidate = nanoid();
    const { data: existing } = await supabase
      .from("trips")
      .select("slug")
      .eq("slug", candidate)
      .maybeSingle();
    if (!existing) {
      slug = candidate;
      break;
    }
  }
  if (!slug) {
    return NextResponse.json(
      { error: "Could not generate a unique trip code. Please try again." },
      { status: 500 }
    );
  }

  // auto_delete_at: 24h after travel date
  const autoDeleteAt = new Date(travelDate);
  autoDeleteAt.setDate(autoDeleteAt.getDate() + 1);

  const { data: inserted, error: insertErr } = await supabase
    .from("trips")
    .insert({
      slug,
      organizer_id: user.id,
      name,
      train_number: trainNumber,
      travel_date: travelDate.toISOString().slice(0, 10),
      deadline: deadline.toISOString(),
      expected_count: expectedCount,
      id_proof_required: idProofRequired,
      auto_delete_at: autoDeleteAt.toISOString(),
      status: "active",
    })
    .select("slug")
    .single();

  if (insertErr || !inserted) {
    console.error("Trip insert failed:", insertErr);
    return NextResponse.json({ error: "Failed to create trip" }, { status: 500 });
  }

  return NextResponse.json({ slug: inserted.slug }, { status: 201 });
}
