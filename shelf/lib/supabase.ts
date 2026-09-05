import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/** The browser Supabase client, created on first use.
 *
 *  Deliberately lazy: building the app should not require credentials, so the
 *  config check happens when the client is actually needed rather than at
 *  module load, where it would fail `next build`.
 *
 *  Only ever holds the anon key — the service-role key must never reach the
 *  browser. */
export function getSupabase(): SupabaseClient {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error(
      "Missing Supabase config. Copy shelf/.env.example to shelf/.env.local and set " +
        "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.",
    );
  }

  client = createClient(url, anonKey);
  return client;
}
