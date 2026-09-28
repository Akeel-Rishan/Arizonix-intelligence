import "server-only";

import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { getPublicAuthConfig } from "@/lib/config";

export async function createSupabaseServerClient() {
  const config = getPublicAuthConfig();
  const cookieStore = await cookies();

  return createServerClient(config.supabaseUrl, config.supabasePublishableKey, {
    cookieOptions: { path: "/", sameSite: "lax", secure: config.siteUrl.startsWith("https://") },
    cookies: {
      getAll: () => cookieStore.getAll(),
      setAll: (cookiesToSet) => {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // Server Components cannot write cookies; proxy.ts performs refresh writes.
        }
      },
    },
  });
}
