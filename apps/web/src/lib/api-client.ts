import type { HealthResponse, MeResponse } from "@/lib/types";
import { parsePublicApiBaseUrl, PublicConfigurationError } from "@/lib/config";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const REQUEST_TIMEOUT_MS = 5_000;

export class HealthCheckError extends Error {
  constructor(public readonly userMessage: string) {
    super(userMessage);
    this.name = "HealthCheckError";
  }
}

export class IdentityRequestError extends Error {
  constructor(
    public readonly kind: "authentication" | "configuration" | "unavailable" | "invalid-response",
    public readonly userMessage: string,
  ) {
    super(userMessage);
    this.name = "IdentityRequestError";
  }
}

function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.status === "ok" &&
    candidate.service === "arizonix-api" &&
    typeof candidate.version === "string" &&
    candidate.version.length > 0
  );
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort("timeout"), REQUEST_TIMEOUT_MS);
  const abortFromCaller = () => timeoutController.abort("cancelled");
  signal?.addEventListener("abort", abortFromCaller, { once: true });

  try {
    let apiBaseUrl: string;
    try {
      apiBaseUrl = parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
    } catch (error: unknown) {
      if (error instanceof PublicConfigurationError) {
        throw new HealthCheckError(error.userMessage);
      }
      throw error;
    }

    const response = await fetch(`${apiBaseUrl}/api/v1/health`, {
      headers: { Accept: "application/json" },
      method: "GET",
      signal: timeoutController.signal,
    });
    if (!response.ok) {
      throw new HealthCheckError("The API returned an error. Confirm it is running and retry.");
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new HealthCheckError(
        "The API response was not recognized. Check that both apps are current.",
      );
    }
    if (!isHealthResponse(payload)) {
      throw new HealthCheckError(
        "The API response was not recognized. Check that both apps are current.",
      );
    }
    return payload;
  } catch (error: unknown) {
    if (error instanceof HealthCheckError) throw error;
    if (timeoutController.signal.reason === "timeout") {
      throw new HealthCheckError("The API request timed out. Check the backend and retry.");
    }
    if (signal?.aborted) {
      throw error;
    }
    throw new HealthCheckError("The API could not be reached. Start the backend and retry.");
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener("abort", abortFromCaller);
  }
}

function isMeResponse(value: unknown): value is MeResponse {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.user_id === "string" &&
    (typeof candidate.email === "string" || candidate.email === null)
  );
}

let refreshPromise: ReturnType<
  ReturnType<typeof createSupabaseBrowserClient>["auth"]["refreshSession"]
> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const supabase = createSupabaseBrowserClient();
  refreshPromise ??= supabase.auth.refreshSession().finally(() => {
    refreshPromise = null;
  });
  const { data, error } = await refreshPromise;
  if (error) return null;
  return data.session?.access_token ?? null;
}

async function requestMe(apiBaseUrl: string, accessToken: string, signal?: AbortSignal) {
  return fetch(`${apiBaseUrl}/api/v1/me`, {
    method: "GET",
    headers: { Accept: "application/json", Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
    signal,
  });
}

export async function fetchCurrentPrincipal(signal?: AbortSignal): Promise<MeResponse> {
  let apiBaseUrl: string;
  try {
    apiBaseUrl = parsePublicApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  } catch (error: unknown) {
    if (error instanceof PublicConfigurationError) {
      throw new IdentityRequestError("configuration", error.userMessage);
    }
    throw error;
  }

  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  let token = data.session?.access_token;
  if (!token) {
    throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
  }

  let response: Response;
  try {
    response = await requestMe(apiBaseUrl, token, signal);
    if (response.status === 401) {
      token = (await refreshAccessToken()) ?? undefined;
      if (!token) {
        throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
      }
      response = await requestMe(apiBaseUrl, token, signal);
    }
  } catch (error: unknown) {
    if (error instanceof IdentityRequestError || signal?.aborted) throw error;
    throw new IdentityRequestError("unavailable", "The identity service could not be reached.");
  }

  if (response.status === 401) {
    throw new IdentityRequestError("authentication", "Your session has ended. Sign in again.");
  }
  if (response.status === 503) {
    throw new IdentityRequestError(
      "unavailable",
      "Authentication verification is unavailable on the API.",
    );
  }
  if (!response.ok) {
    throw new IdentityRequestError("unavailable", "The identity service returned an error.");
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new IdentityRequestError("invalid-response", "The identity response was not recognized.");
  }
  if (!isMeResponse(payload)) {
    throw new IdentityRequestError("invalid-response", "The identity response was not recognized.");
  }
  return payload;
}
