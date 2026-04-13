import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * Magic-link callback.
 *
 * Supabase redirects here with a ?code=... param after the user clicks the
 * email link. We exchange the code for a session, set the session cookie,
 * and redirect to the dashboard.
 */
export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  // Fall through: send them to the login page with an error
  return NextResponse.redirect(`${origin}/login?error=auth_failed`);
}
