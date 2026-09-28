import { redirect } from "next/navigation";
import { connection } from "next/server";
import type { ReactNode } from "react";

import { AuthSetupUnavailable } from "@/components/auth/auth-setup-unavailable";
import { AppShell } from "@/components/layout/app-shell";
import { PublicConfigurationError } from "@/lib/config";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function ProtectedLayout({ children }: { children: ReactNode }) {
  await connection();
  let claims: Record<string, unknown> | undefined;
  try {
    const supabase = await createSupabaseServerClient();
    const result = await supabase.auth.getClaims();
    claims = result.data?.claims;
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) return <AuthSetupUnavailable />;
    redirect("/login");
  }
  if (!claims) redirect("/login");
  const email = typeof claims.email === "string" ? claims.email : null;
  return <AppShell email={email}>{children}</AppShell>;
}
