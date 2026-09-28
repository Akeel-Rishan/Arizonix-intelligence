"use client";

import { createBrowserClient } from "@supabase/ssr";

import { getPublicAuthConfig } from "@/lib/config";

let browserClient: ReturnType<typeof createBrowserClient> | undefined;

export function createSupabaseBrowserClient() {
  if (browserClient) return browserClient;
  const config = getPublicAuthConfig();
  browserClient = createBrowserClient(config.supabaseUrl, config.supabasePublishableKey, {
    cookieOptions: { path: "/", sameSite: "lax", secure: config.siteUrl.startsWith("https://") },
  });
  return browserClient;
}
