import type { EmailOtpType } from "@supabase/supabase-js";
import { NextResponse, type NextRequest } from "next/server";

import { safeRedirectPath } from "@/lib/auth/redirect";
import { getPublicAuthConfig } from "@/lib/config";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const tokenHash = request.nextUrl.searchParams.get("token_hash");
  const type = request.nextUrl.searchParams.get("type");
  const destination = safeRedirectPath(request.nextUrl.searchParams.get("next"));
  let siteUrl: string;

  try {
    siteUrl = getPublicAuthConfig().siteUrl;
    if (tokenHash && type === "email") {
      const supabase = await createSupabaseServerClient();
      const { error } = await supabase.auth.verifyOtp({
        token_hash: tokenHash,
        type: type as EmailOtpType,
      });
      if (!error) return NextResponse.redirect(new URL(destination, siteUrl));
    }
  } catch {
    // Configuration and provider failures use the same token-free failure path.
    siteUrl = request.nextUrl.origin;
  }
  return NextResponse.redirect(new URL("/login?confirmation=expired", siteUrl));
}
