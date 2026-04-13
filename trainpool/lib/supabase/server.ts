import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for use in:
 *   - React Server Components (pages, layouts)
 *   - Route Handlers (app/api/.../route.ts)
 *   - Server Actions
 *
 * Uses the anon key + user's session cookie. For service-role operations
 * (e.g., reading encrypted columns, bypassing RLS), use createServiceClient() below.
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // Called from a Server Component — the middleware will handle the refresh
          }
        },
      },
    }
  );
}

/**
 * Service-role client for admin operations. NEVER expose this to the browser.
 * Used for: reading encrypted passenger data, running the generate-block endpoint,
 * bypassing RLS when we've already verified ownership in app code.
 */
import { createClient as createBaseClient } from "@supabase/supabase-js";

export function createServiceClient() {
  return createBaseClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: { autoRefreshToken: false, persistSession: false },
    }
  );
}
