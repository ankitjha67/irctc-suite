/**
 * POST /api/trips/[slug]/generate-block
 *
 * Organizer-only endpoint. Decrypts all passenger IDs in memory and returns
 * the TSV paste block. Never persists the decrypted block.
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { generateBlock } from "@/lib/paste-block";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;

  // Service role client — we need to read encrypted bytes + check ownership server-side
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  // Extract the authenticated organizer from the request
  const authHeader = req.headers.get("authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const accessToken = authHeader.slice(7);
  const { data: userData, error: userErr } = await supabase.auth.getUser(accessToken);
  if (userErr || !userData.user) {
    return NextResponse.json({ error: "Invalid session" }, { status: 401 });
  }

  // Fetch trip + verify ownership
  const { data: trip, error: tripErr } = await supabase
    .from("trips")
    .select("id, slug, organizer_id, id_proof_required, status")
    .eq("slug", slug)
    .single();

  if (tripErr || !trip) {
    return NextResponse.json({ error: "Trip not found" }, { status: 404 });
  }
  if (trip.organizer_id !== userData.user.id) {
    return NextResponse.json({ error: "Not your trip" }, { status: 403 });
  }

  // Fetch passengers
  const { data: passengers, error: paxErr } = await supabase
    .from("passengers")
    .select(
      "full_name, age, gender, berth_preference, id_type, id_number_encrypted"
    )
    .eq("trip_id", trip.id)
    .order("submitted_at", { ascending: true });

  if (paxErr) {
    return NextResponse.json({ error: "Failed to load passengers" }, { status: 500 });
  }

  // Supabase returns bytea as base64 string — convert to Buffer
  const normalized = (passengers ?? []).map((p) => ({
    ...p,
    id_number_encrypted: p.id_number_encrypted
      ? Buffer.from(p.id_number_encrypted as unknown as string, "base64")
      : null,
  }));

  const block = generateBlock(normalized as Parameters<typeof generateBlock>[0], slug, {
    idProofRequired: trip.id_proof_required,
  });

  return NextResponse.json({
    trip_name: slug,
    ...block,
  });
}
