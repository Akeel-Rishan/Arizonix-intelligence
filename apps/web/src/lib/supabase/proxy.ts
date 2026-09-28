import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

import { safeRedirectPath } from "@/lib/auth/redirect";
import { getPublicAuthConfig, PublicConfigurationError } from "@/lib/config";

const PROTECTED_PATHS = ["/", "/prospects", "/research", "/evidence", "/review", "/settings"];

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PATHS.some((path) =>
    path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`),
  );
}

function copySessionResponse(source: NextResponse, target: NextResponse): NextResponse {
  source.cookies.getAll().forEach((cookie) => target.cookies.set(cookie));
  for (const header of ["cache-control", "pragma", "expires"]) {
    const value = source.headers.get(header);
    if (value) target.headers.set(header, value);
  }
  return target;
}

export async function updateSession(request: NextRequest): Promise<NextResponse> {
  let response = NextResponse.next({ request });
  let authConfig;
  try {
    authConfig = getPublicAuthConfig();
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) return response;
    throw error;
  }

  const supabase = createServerClient(authConfig.supabaseUrl, authConfig.supabasePublishableKey, {
    cookieOptions: {
      path: "/",
      sameSite: "lax",
      secure: authConfig.siteUrl.startsWith("https://"),
    },
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (
        cookiesToSet: { name: string; value: string; options: CookieOptions }[],
        headers: Record<string, string>,
      ) => {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
        Object.entries(headers).forEach(([name, value]) => response.headers.set(name, value));
      },
    },
  });

  let claims: Record<string, unknown> | undefined;
  try {
    const { data } = await supabase.auth.getClaims();
    claims = data?.claims;
  } catch {
    claims = undefined;
  }
  if (!claims && isProtectedPath(request.nextUrl.pathname)) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.search = "";
    const requested = `${request.nextUrl.pathname}${request.nextUrl.search}`;
    loginUrl.searchParams.set("next", safeRedirectPath(requested));
    return copySessionResponse(response, NextResponse.redirect(loginUrl));
  }
  return response;
}
