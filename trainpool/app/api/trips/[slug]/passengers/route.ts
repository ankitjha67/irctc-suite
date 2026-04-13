/**
 * POST /api/trips/[slug]/passengers
 * Public endpoint — anyone with the slug can add a passenger until the deadline.
 * Returns an edit_token cookie so the same device can edit its own submission.
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import {
  encryptIdNumber,
  generateEditToken,
  hashEditToken,
} from "@/lib/encryption";
import { validatePassengerInput } from "@/lib/paste-block";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  const body = await req.json().catch(() => null);

  const validation = validatePassengerInput(body);
  if (!validation.ok) {
    return NextResponse.json(
      { error: "Validation failed", details: validation.errors },
      { status: 400 }
    );
  }

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  // Fetch trip, verify it's active and not past deadline
  const { data: trip } = await supabase
    .from("trips")
    .select("id, slug, deadline, status, expected_count, id_proof_required")
    .eq("slug", slug)
    .single();

  if (!trip) {
    return NextResponse.json({ error: "Trip not found" }, { status: 404 });
  }
  if (trip.status !== "active") {
    return NextResponse.json({ error: "Trip is locked" }, { status: 403 });
  }
  if (new Date(trip.deadline) < new Date()) {
    return NextResponse.json({ error: "Deadline has passed" }, { status: 403 });
  }

  // Check passenger count cap
  const { count } = await supabase
    .from("passengers")
    .select("*", { count: "exact", head: true })
    .eq("trip_id", trip.id);

  if (trip.expected_count && (count ?? 0) >= trip.expected_count) {
    return NextResponse.json({ error: "Trip is full" }, { status: 403 });
  }

  // Encrypt ID number if provided
  let idEncrypted: Buffer | null = null;
  let idHint: string | null = null;
  if (body.id_number) {
    const result = encryptIdNumber(String(body.id_number), slug);
    idEncrypted = result.encrypted;
    idHint = result.hint;
  }

  // Generate + hash edit token
  const editToken = generateEditToken();
  const editTokenHash = hashEditToken(editToken);

  const { data: inserted, error: insertErr } = await supabase
    .from("passengers")
    .insert({
      trip_id: trip.id,
      full_name: body.full_name.trim(),
      age: Number(body.age),
      gender: body.gender,
      berth_preference: body.berth_preference ?? null,
      id_type: body.id_type ?? null,
      id_number_encrypted: idEncrypted,
      id_number_hint: idHint,
      edit_token_hash: editTokenHash,
    })
    .select("id")
    .single();

  if (insertErr || !inserted) {
    return NextResponse.json({ error: "Failed to save" }, { status: 500 });
  }

  // Set edit_token as HttpOnly cookie, scoped to this trip's path
  const response = NextResponse.json({
    ok: true,
    passenger_id: inserted.id,
  });

  response.cookies.set(`tp_edit_${slug}`, editToken, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: `/trip/${slug}`,
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });

  return response;
}
